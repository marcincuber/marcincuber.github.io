"""Explicit online checks for outbound links and a completed Pages deployment."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import time
from typing import Literal
from urllib.parse import quote, urldefrag, urljoin, urlsplit

from .network import FetchError, fetch
from .reports import markdown_text, write_summary


class CheckError(ValueError):
    """A check cannot run against the supplied site or build."""


def site_base(url: str) -> str:
    parsed = urlsplit(url)
    local = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (not parsed.hostname or (parsed.scheme != "https" and not local)
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise CheckError("site URL must be HTTPS (or local HTTP), without credentials or a query")
    return url.rstrip("/") + "/"


class OutboundLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.add(href)


def external_links(output: Path, site_url: str) -> list[str]:
    base = site_base(site_url)
    pages = sorted(output.rglob("*.html"))
    if not pages:
        raise CheckError(f"no generated HTML in {output}; run make build first")
    links: set[str] = set()
    for page in pages:
        parser = OutboundLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        for href in parser.links:
            url = urldefrag(urljoin(base, href))[0]
            parsed = urlsplit(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc != urlsplit(base).netloc:
                links.add(url)
    if not links:
        raise CheckError("no external links found in generated HTML")
    return sorted(links)


@dataclass(frozen=True)
class LinkResult:
    url: str
    state: Literal["passed", "failed"]
    detail: str


def link_result(url: str) -> LinkResult:
    try:
        fetch(url, max_bytes=None, timeout=15)
        return LinkResult(url, "passed", "OK")
    except FetchError as error:
        if error.status in {401, 403, 429}:
            return LinkResult(url, "failed",
                              f"Unverified (access restriction or rate limit): {error}")
        return LinkResult(url, "failed", f"Failed: {error}")


def check_external_links(output: Path, site_url: str, summary: Path | None = None) -> bool:
    urls = external_links(output, site_url)
    medium_urls = [url for url in urls if (urlsplit(url).hostname or "").lower() == "medium.com"
                   or (urlsplit(url).hostname or "").lower().endswith(".medium.com")]
    other_urls = [url for url in urls if url not in medium_urls]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(link_result, other_urls))
    # Serialize across all Medium subdomains instead of sending a burst of requests.
    for index, url in enumerate(medium_urls):
        if index:
            time.sleep(2)
        results.append(link_result(url))
    results.sort(key=lambda result: result.url)
    failed = sum(result.state == "failed" for result in results)
    passed = sum(result.state == "passed" for result in results)
    lines = ["## External-link check", "",
             f"Checked: {len(results)} · Passed: {passed} · Failed: {failed}", "",
             "Access restrictions are unverified links, not proof that a page was deleted.",
             "Every link must respond successfully, including Medium links. "
             "If a host blocks the runner, verify access from another runner before switching.",
             "", "| URL | Result |", "| --- | --- |"]
    lines.extend(f"| {markdown_text(result.url)} | {markdown_text(result.detail)} |"
                 for result in results)
    write_summary(summary, "\n".join(lines))
    return not failed


def check_live_site(output: Path, site_url: str, summary: Path | None = None) -> bool:
    base = site_base(site_url)
    required = ("index.html", "cv/index.html", "cv/Marcin-Cuber-CV.pdf",
                "sitemap.xml", "robots.txt", "site.webmanifest", "404.html")
    if any(not (output / path).is_file() for path in required):
        raise CheckError(f"incomplete production build in {output}; run make build first")
    files = sorted(path for path in output.rglob("*")
                   if path.is_file() and not path.name.startswith("."))
    if any(path.is_symlink() for path in files):
        raise CheckError("refusing to check a build containing symlinked files")

    def verify(path: Path) -> tuple[Path, str]:
        relative = path.relative_to(output).as_posix()
        route = relative.removesuffix("index.html") if path.name == "index.html" else relative
        expected = path.read_bytes()
        # The content digest avoids reusing a cached response from an older deployment.
        url = urljoin(base, quote(route)) + "?deployment-check=" + sha256(expected).hexdigest()
        try:
            actual = fetch(url, max_bytes=len(expected) + 4096, attempts=1)
        except FetchError as error:
            return path, str(error)
        return path, "OK" if actual == expected else "Content differs from the deployed build"

    pending = files
    outcomes: dict[Path, str] = {}
    for attempt in range(4):
        if attempt:
            time.sleep(5 * 2 ** (attempt - 1))
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes.update(pool.map(verify, pending))
        pending = [path for path in files if outcomes[path] != "OK"]
        if not pending:
            break
        print(f"Live-site check: {len(pending)} files pending after attempt {attempt + 1}/4.")

    lines = ["## Live-site check", "", f"Site: {markdown_text(base)}", "",
             f"Verified: {len(files) - len(pending)}/{len(files)} files match the build.", "",
             "| File | Result |", "| --- | --- |"]
    lines.extend(f"| {markdown_text(path.relative_to(output).as_posix())} | "
                 f"{markdown_text(outcomes[path])} |" for path in files)
    write_summary(summary, "\n".join(lines))
    return not pending
