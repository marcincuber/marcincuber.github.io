"""Offline coverage for RSS synchronization and failure-safe profile updates."""

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
import xml.etree.ElementTree as ET

from portfolio_site.__main__ import main
from portfolio_site.builder import PROJECT_ROOT
from portfolio_site.content import ContentError, Profile
from portfolio_site.medium import (
    MAX_FEED_BYTES,
    SyncError,
    article_key,
    feed_url,
    fetch_feed,
    parse_feed,
    sync_medium,
)


def rss_item(
    story_id: str = "abcdef123456",
    *,
    title: str = "New & updated article",
    published: str = "Mon, 19 Oct 2026 12:32:25 GMT",
    description: str = "<p>A <strong>useful</strong> excerpt &amp; example.</p>",
    url: str | None = None,
) -> ET.Element:
    item = ET.Element("item")
    for key, value in {
        "title": title,
        "link": url or f"https://marcincuber.medium.com/new-article-{story_id}?source=rss#ref",
        "pubDate": published,
        "{http://purl.org/rss/1.0/modules/content/}encoded": description,
        "category": "Kubernetes",
    }.items():
        ET.SubElement(item, key).text = value
    return item


def rss(*items: ET.Element) -> bytes:
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    channel.extend(items)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class MediumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.content = Path(self.directory.name) / "profile.json"
        raw = json.loads((PROJECT_ROOT / "content" / "profile.json").read_bytes())
        raw["articles"] = parse_feed(rss(
            rss_item("111111111111", published="01 Jan 2026 12:00:00 GMT"),
            rss_item("222222222222", published="01 Jan 2025 12:00:00 GMT"),
        ))
        self.original = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode()
        self.content.write_bytes(self.original)
        self.feed = Path(self.directory.name) / "feed.xml"
        self.output = io.StringIO()

    def sync(self, payload: bytes, *, dry_run: bool = False) -> bool:
        self.feed.write_bytes(payload)
        with redirect_stdout(self.output):
            return sync_medium(self.content, feed_file=self.feed, dry_run=dry_run)

    def test_feed_url_uses_profile(self) -> None:
        self.assertEqual(feed_url("https://marcincuber.medium.com/"),
                         "https://marcincuber.medium.com/feed")
        self.assertEqual(feed_url("https://medium.com/@marcincuber"),
                         "https://medium.com/feed/@marcincuber")
        with self.assertRaises(SyncError):
            feed_url("https://example.com/")

    def test_metadata_is_plain_text_and_tracking_is_removed(self) -> None:
        article = parse_feed(rss(rss_item()))[0]
        self.assertEqual(article["title"], "New & updated article")
        self.assertEqual(article["description"], "A useful excerpt & example.")
        self.assertEqual(article["date"], "2026-10-19")
        self.assertEqual(article["display_date"], "19 Oct 2026")
        self.assertEqual(article["topic"], "Kubernetes")
        self.assertEqual(article["url"],
                         "https://marcincuber.medium.com/new-article-abcdef123456")

    def test_paywall_description_missing_categories_and_utc_dates(self) -> None:
        item = rss_item(published="Mon, 19 Oct 2026 00:30:00 +0200")
        item.remove(item.find("category"))
        ET.SubElement(item, "description").text = (
            "<script>hidden()</script><style>bad{}</style><p>Public preview.</p>"
        )
        article = parse_feed(rss(item))[0]
        self.assertEqual(article["description"], "Public preview.")
        self.assertEqual(article["topic"], "Technical writing")
        self.assertEqual(article["date"], "2026-10-18")

    def test_long_excerpts_are_bounded_and_missing_excerpts_use_title(self) -> None:
        article = parse_feed(rss(rss_item(description="some words " * 100)))[0]
        self.assertLessEqual(len(article["description"]), 240)
        self.assertTrue(article["description"].endswith("…"))
        article = parse_feed(rss(rss_item(description="")))[0]
        self.assertEqual(article["description"], article["title"])

    def test_excerpt_uses_first_block_without_headings_or_image_captions(self) -> None:
        article = parse_feed(rss(rss_item(description=(
            "<h1>Repeated title</h1><figure><img src='image'><figcaption>Caption</figcaption>"
            "</figure><h3>Overview</h3><p>The introduction.</p><p>The rest of the article.</p>"
        ))))[0]
        self.assertEqual(article["description"], "The introduction.")

    def test_merge_keeps_older_articles_and_unrelated_profile_data(self) -> None:
        before = json.loads(self.original)
        self.assertTrue(self.sync(rss(rss_item())))
        after = json.loads(self.content.read_bytes())
        self.assertEqual(after["articles"][0]["title"], "New & updated article")
        old_ids = {article_key(item["url"]) for item in before["articles"]}
        new_ids = {article_key(item["url"]) for item in after["articles"]}
        self.assertTrue(old_ids.issubset(new_ids))
        before.pop("articles")
        after.pop("articles")
        self.assertEqual(before, after)
        self.assertEqual(self.original.split(b'"articles":')[0],
                         self.content.read_bytes().split(b'"articles":')[0])
        self.assertEqual(self.original.split(b'"career":')[1],
                         self.content.read_bytes().split(b'"career":')[1])

    def test_existing_story_updates_across_hosts_and_changed_slugs(self) -> None:
        before = json.loads(self.original)
        story_id = article_key(before["articles"][0]["url"])
        item = rss_item(story_id, url=f"https://medium.com/@marcincuber/changed-{story_id}")
        self.sync(rss(item, item))
        after = json.loads(self.content.read_bytes())
        self.assertEqual(len(after["articles"]), len(before["articles"]))
        matches = [article for article in after["articles"]
                   if article_key(article["url"]) == story_id]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["title"], "New & updated article")

    def test_newest_twelve_are_kept_regardless_of_feed_order(self) -> None:
        items = [rss_item(f"{index:012x}", published=f"{index:02d} Nov 2026 12:00:00 GMT")
                 for index in range(1, 21)]
        self.sync(rss(*items))
        articles = Profile.load(self.content).articles
        self.assertEqual(len(articles), 12)
        self.assertEqual(articles[0].date, "2026-11-20")
        self.assertEqual(articles[-1].date, "2026-11-09")
        saved = self.content.read_bytes()
        self.assertFalse(self.sync(rss(*reversed(items))))
        self.assertEqual(self.content.read_bytes(), saved)

    def test_repeat_run_does_not_rewrite_the_file(self) -> None:
        payload = rss(rss_item())
        self.sync(payload)
        before = self.content.stat()
        saved = self.content.read_bytes()
        self.assertFalse(self.sync(payload))
        after = self.content.stat()
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
        self.assertEqual(before.st_ino, after.st_ino)
        self.assertEqual(saved, self.content.read_bytes())

    def test_dry_run_validates_without_changing_content(self) -> None:
        self.assertTrue(self.sync(rss(rss_item()), dry_run=True))
        self.assertEqual(self.original, self.content.read_bytes())
        self.assertIn("Would sync", self.output.getvalue())
        self.assertEqual(list(self.content.parent.glob("*.json")), [self.content])

    def test_bad_feed_or_item_leaves_snapshot_untouched(self) -> None:
        for payload in (
            b"not xml", b"<html>error page</html>", rss(),
            rss(rss_item(), rss_item(title="")),
            rss(rss_item(published="invalid")),
            rss(rss_item(published="19 Oct 2026 12:00:00")),
            rss(rss_item(url="http://medium.com/unsafe")),
            rss(rss_item(url="https://user:password@medium.com/unsafe")),
            rss(rss_item(url="https://[bad-host")),
        ):
            with self.subTest(payload=payload[:100]):
                with self.assertRaises((SyncError, ContentError)):
                    self.sync(payload)
                self.assertEqual(self.original, self.content.read_bytes())

    def test_network_error_leaves_snapshot_untouched(self) -> None:
        with patch("portfolio_site.medium.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(SyncError, "could not fetch"):
                sync_medium(self.content)
        self.assertEqual(self.original, self.content.read_bytes())

    def test_fetch_uses_timeout_and_rejects_oversized_responses(self) -> None:
        with patch("portfolio_site.medium.urlopen") as request:
            response = request.return_value.__enter__.return_value
            response.read.return_value = b"x" * (MAX_FEED_BYTES + 1)
            with self.assertRaisesRegex(SyncError, "size limit"):
                fetch_feed("https://marcincuber.medium.com/feed")
            self.assertEqual(request.call_args.kwargs["timeout"], 30)
            response.read.assert_called_once_with(MAX_FEED_BYTES + 1)

    def test_candidate_validation_failure_leaves_snapshot_untouched(self) -> None:
        self.feed.write_bytes(rss(rss_item()))
        profile = Profile.load(self.content)
        with patch("portfolio_site.medium.Profile.load", side_effect=[
            profile, ContentError("invalid candidate"),
        ]):
            with self.assertRaises(ContentError):
                sync_medium(self.content, feed_file=self.feed)
        self.assertEqual(self.original, self.content.read_bytes())
        self.assertEqual(list(self.content.parent.glob("*.json")), [self.content])

    def test_content_validation_rejects_more_than_twelve_articles(self) -> None:
        profile = Profile.load(self.content)
        oversized = replace(profile, articles=(profile.articles[0],) * 13)
        with self.assertRaisesRegex(ContentError, "at most 12"):
            oversized.validate()

    def test_cli_failure_returns_nonzero_without_traceback(self) -> None:
        self.feed.write_bytes(b"broken feed")
        with patch("sys.argv", [
            "portfolio-site", "sync-medium", "--content", str(self.content),
            "--feed-file", str(self.feed),
        ]), redirect_stdout(self.output):
            self.assertEqual(main(), 2)
        self.assertIn("invalid Medium RSS", self.output.getvalue())
        self.assertEqual(self.original, self.content.read_bytes())


if __name__ == "__main__":
    unittest.main()
