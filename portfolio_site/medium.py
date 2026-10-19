"""Explicit, build-independent synchronization of the public Medium RSS feed."""

from __future__ import annotations

from datetime import timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .content import Article, MAX_ARTICLES, Profile

MAX_FEED_BYTES = 5 * 1024 * 1024
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


class SyncError(ValueError):
    """The feed cannot safely update the saved article snapshot."""


class PlainText(HTMLParser):
    """Extract readable text without including scripts, styles or image markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "h1", "h2", "h3", "figcaption"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "li", "figure", "figcaption", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "h1", "h2", "h3", "figcaption"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "li", "figure", "figcaption", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(markup: str, *, first_block: bool = False) -> str:
    parser = PlainText()
    parser.feed(markup)
    parser.close()
    blocks = [" ".join(block.split()) for block in "".join(parser.parts).splitlines()]
    nonempty = [block for block in blocks if block]
    return next(iter(nonempty), "") if first_block else " ".join(nonempty)


def clean_url(url: str) -> str:
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("expected an absolute HTTPS URL without credentials")
        return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, "", ""))
    except ValueError as error:
        raise SyncError(f"invalid article URL: {url!r}") from error


def article_key(url: str) -> str:
    """Medium's stable story ID survives slug, publication and hostname changes."""
    canonical = clean_url(url)
    match = re.search(r"(?:-|/)([0-9a-f]{12})/?$", urlsplit(canonical).path)
    return match.group(1) if match else canonical


def feed_url(profile_url: str) -> str:
    parsed = urlsplit(profile_url)
    if parsed.hostname in {"medium.com", "www.medium.com"}:
        if re.fullmatch(r"/@[\w.-]+/?", parsed.path):
            return f"https://medium.com/feed/{parsed.path.strip('/')}"
    elif parsed.hostname and re.fullmatch(r"[\w-]+\.medium\.com", parsed.hostname):
        if parsed.path in {"", "/"}:
            return f"https://{parsed.hostname}/feed"
    raise SyncError("site.medium_url must be a Medium author profile URL")


def fetch_feed(url: str) -> bytes:
    request = Request(url, headers={
        "User-Agent": "marcincuber-portfolio/1.0 (+https://marcincuber.github.io)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
    except (OSError, ValueError) as error:
        raise SyncError(f"could not fetch Medium feed: {error}") from error
    if len(payload) > MAX_FEED_BYTES:
        raise SyncError("Medium feed exceeds the 5 MiB size limit")
    return payload


def parse_feed(payload: bytes) -> list[dict[str, str]]:
    if len(payload) > MAX_FEED_BYTES:
        raise SyncError("Medium feed exceeds the 5 MiB size limit")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise SyncError(f"invalid Medium RSS XML: {error}") from error
    items = root.findall("./channel/item") if root.tag == "rss" else []
    if not items:
        raise SyncError("Medium feed contains no articles; keeping the saved snapshot")

    articles = []
    for index, item in enumerate(items):
        title = " ".join(unescape(item.findtext("title", "")).split())
        url = clean_url(item.findtext("link", ""))
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
            if published.tzinfo is None:
                raise ValueError("publication date must include a timezone")
            published = published.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError) as error:
            raise SyncError(f"invalid publication date for {title!r}") from error
        markup = item.findtext("description") or item.findtext(
            "{http://purl.org/rss/1.0/modules/content/}encoded", ""
        )
        description = plain_text(markup, first_block=True) or title
        if len(description) > 240:
            description = description[:237].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        topic = next(
            (plain_text(category.text or "") for category in item.findall("category")
             if plain_text(category.text or "")),
            "Technical writing",
        )
        article = {
            "title": title,
            "date": published.date().isoformat(),
            "display_date": f"{published.day:02d} {MONTHS[published.month - 1]} {published.year}",
            "topic": topic,
            "description": description,
            "url": url,
        }
        Article.from_record(article, f"feed[{index}]")
        articles.append(article)
    return articles


def replace_articles(source: str, articles: list[dict[str, str]]) -> str:
    """Replace the top-level JSON value without reformatting unrelated profile data."""
    decoder = json.JSONDecoder()
    position = source.index("{") + 1
    while True:
        position += len(source[position:]) - len(source[position:].lstrip())
        key, position = decoder.raw_decode(source, position)
        position = source.index(":", position) + 1
        position += len(source[position:]) - len(source[position:].lstrip())
        start = position
        _, position = decoder.raw_decode(source, position)
        if key == "articles":
            replacement = json.dumps(articles, ensure_ascii=False, indent=2).replace("\n", "\n  ")
            return source[:start] + replacement + source[position:]
        position = source.index(",", position) + 1


def sync_medium(content: Path, *, feed_file: Path | None = None, dry_run: bool = False) -> bool:
    """Merge recent feed entries, validate, and atomically replace only changed data."""
    profile = Profile.load(content)
    original = content.read_text(encoding="utf-8")
    raw = json.loads(original)
    payload = feed_file.read_bytes() if feed_file else fetch_feed(feed_url(profile.site.medium_url))
    incoming = parse_feed(payload)
    merged = {article_key(article["url"]): article for article in raw["articles"]}
    # Sort first so a duplicated feed ID consistently selects its newest entry.
    for article in sorted(incoming, key=lambda item: (item["date"], item["url"], item["title"])):
        merged[article_key(article["url"])] = article
    raw["articles"] = sorted(
        merged.values(), key=lambda item: (item["date"], article_key(item["url"])), reverse=True
    )[:MAX_ARTICLES]
    updated = replace_articles(original, raw["articles"])
    if json.loads(original) == raw:
        print(f"Medium articles unchanged ({len(raw['articles'])} saved).")
        return False

    # Validate the complete candidate before replacement; failures leave the original intact.
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=content.parent, suffix=".json", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(updated)
        Profile.load(temporary)
        if dry_run:
            print(f"Would sync Medium articles ({len(raw['articles'])} saved; limit {MAX_ARTICLES}).")
        else:
            if content.read_text(encoding="utf-8") != original:
                raise SyncError("profile changed during synchronization; please run again")
            temporary.chmod(content.stat().st_mode & 0o777)
            temporary.replace(content)
            print(f"Synced Medium articles ({len(raw['articles'])} saved; limit {MAX_ARTICLES}).")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True
