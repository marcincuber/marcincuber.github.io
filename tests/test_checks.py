"""Offline tests of link inventory, deployed content verification and reports."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from portfolio_site.__main__ import main
from portfolio_site.checks import (
    CheckError, check_external_links, check_live_site, external_links, site_base,
)
from portfolio_site.network import FetchError


class OnlineCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "dist"
        self.output.mkdir()
        self.summary = Path(self.directory.name) / "summary.md"
        self.stdout = io.StringIO()
        sleeper = patch("portfolio_site.checks.time.sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def write(self, name: str, content: str) -> None:
        path = self.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def production_files(self) -> None:
        for name in ("index.html", "cv/index.html", "cv/Marcin-Cuber-CV.pdf", "404.html",
                     "sitemap.xml", "robots.txt", "site.webmanifest", "assets/site.hash.css"):
            self.write(name, f"expected {name}")
        self.write(".nojekyll", "")

    def deployed(self, url: str, **kwargs: object) -> bytes:
        route = unquote(urlsplit(url).path).removeprefix("/portfolio/")
        if not route or route.endswith("/"):
            route += "index.html"
        return (self.output / route).read_bytes()

    def test_external_links_are_deduplicated_without_internal_or_email_links(self) -> None:
        markup = ('<a href="https://other.example/a#one">one</a>'
                  '<a href="https://other.example/a#two">two</a>'
                  '<a href="https://other.example/search?q=hello&amp;x=1">query</a>'
                  '<a href="https://site.example/cv/">CV</a><a href="/">Home</a>'
                  '<a href="mailto:hello@example.com">Email</a>'
                  '<a href="//another.example/">Protocol relative</a>')
        self.write("index.html", markup)
        self.write("cv/index.html", markup)
        self.assertEqual(external_links(self.output, "https://site.example/"), [
            "https://another.example/", "https://other.example/a",
            "https://other.example/search?q=hello&x=1",
        ])

    def test_failed_and_blocked_links_are_reported_with_nonzero_cli_status(self) -> None:
        self.write("index.html", '<a href="https://other.example/">Other</a>')
        for status, label in ((404, "Failed"), (403, "Unverified"), (429, "Unverified")):
            with self.subTest(status=status), patch("portfolio_site.checks.fetch",
                side_effect=FetchError(f"HTTP {status}", status)), patch("sys.argv", [
                    "portfolio-site", "check-links", "--output", str(self.output),
                    "--site-url", "https://site.example/", "--summary", str(self.summary),
                ]), redirect_stdout(self.stdout):
                self.assertEqual(main(), 1)
            self.assertIn(label, self.summary.read_text())

    def test_successful_links_are_reported(self) -> None:
        self.write("index.html", '<a href="https://other.example/">Other</a>')
        with patch("portfolio_site.checks.fetch", return_value=b""), redirect_stdout(self.stdout):
            self.assertTrue(check_external_links(self.output, "https://site.example/", self.summary))
        self.assertIn("Checked: 1 · Passed: 1 · Warnings: 0 · Failed: 0", self.summary.read_text())

    def test_medium_restrictions_warn_but_allow_successful_cli_exit(self) -> None:
        for host in ("medium.com", "marcincuber.medium.com", "MEDIUM.COM"):
            for status in (403, 429):
                self.write("index.html", f'<a href="https://{host}/article">Article</a>')
                self.summary.write_text("")
                with self.subTest(host=host, status=status), patch(
                    "portfolio_site.checks.fetch", side_effect=FetchError(f"HTTP {status}", status)
                ), patch("sys.argv", [
                    "portfolio-site", "check-links", "--output", str(self.output),
                    "--site-url", "https://site.example/", "--summary", str(self.summary),
                ]), redirect_stdout(self.stdout):
                    self.assertEqual(main(), 0)
                report = self.summary.read_text()
                self.assertIn("Passed: 0 · Warnings: 1 · Failed: 0", report)
                self.assertIn("Unverified Medium link", report)
                self.assertIn(str(status), report)

    def test_other_medium_errors_still_fail(self) -> None:
        self.write("index.html", '<a href="https://marcincuber.medium.com/article">Article</a>')
        for status in (401, 404, 410, 500, 503, None):
            with self.subTest(status=status), patch(
                "portfolio_site.checks.fetch", side_effect=FetchError("failure", status)
            ), redirect_stdout(self.stdout):
                self.assertFalse(check_external_links(self.output, "https://site.example/"))

    def test_medium_policy_does_not_match_lookalike_hosts(self) -> None:
        for host in ("notmedium.com", "medium.com.example.org", "medium.com@other.example"):
            self.write("index.html", f'<a href="https://{host}/article">Article</a>')
            with self.subTest(host=host), patch(
                "portfolio_site.checks.fetch", side_effect=FetchError("HTTP 429", 429)
            ), redirect_stdout(self.stdout):
                self.assertFalse(check_external_links(self.output, "https://site.example/"))

    def test_medium_warning_does_not_hide_a_broken_link(self) -> None:
        self.write("index.html", '<a href="https://medium.com/article">Medium</a>'
                   '<a href="https://other.example/missing">Broken</a>'
                   '<a href="https://other.example/working">Working</a>')

        def probe(url: str, **kwargs: object) -> bytes:
            if urlsplit(url).hostname == "medium.com":
                raise FetchError("HTTP 429", 429)
            if url.endswith("/missing"):
                raise FetchError("HTTP 404", 404)
            return b""

        with patch("portfolio_site.checks.fetch", side_effect=probe), redirect_stdout(self.stdout):
            self.assertFalse(check_external_links(self.output, "https://site.example/", self.summary))
        self.assertIn("Checked: 3 · Passed: 1 · Warnings: 1 · Failed: 1", self.summary.read_text())

    def test_live_check_compares_all_files_including_pdf_and_assets(self) -> None:
        self.production_files()
        with (patch("portfolio_site.checks.fetch", side_effect=self.deployed) as request,
              redirect_stdout(self.stdout)):
            self.assertTrue(check_live_site(self.output, "https://site.example/portfolio/",
                                            self.summary))
        self.assertEqual(request.call_count, 8)
        self.assertIn("Verified: 8/8", self.summary.read_text())
        self.sleep.assert_not_called()

    def test_live_check_retries_only_stale_files(self) -> None:
        self.production_files()
        stale = True

        def delayed(url: str, **kwargs: object) -> bytes:
            nonlocal stale
            if urlsplit(url).path == "/portfolio/" and stale:
                stale = False
                return b"old deployment"
            return self.deployed(url)

        with (patch("portfolio_site.checks.fetch", side_effect=delayed) as request,
              redirect_stdout(self.stdout)):
            self.assertTrue(check_live_site(self.output, "https://site.example/portfolio/"))
        self.assertEqual(request.call_count, 9)
        self.sleep.assert_called_once_with(5)

    def test_live_missing_asset_or_wrong_content_fails_after_retries(self) -> None:
        self.production_files()
        for failure in (FetchError("HTTP 404", 404), None):
            def broken(url: str, **kwargs: object) -> bytes:
                if "/assets/" in url:
                    if failure:
                        raise failure
                    return b"wrong content despite HTTP 200"
                return self.deployed(url)

            with (patch("portfolio_site.checks.fetch", side_effect=broken) as request,
                  redirect_stdout(self.stdout)):
                self.assertFalse(check_live_site(self.output, "https://site.example/portfolio/",
                                                 self.summary))
            self.assertEqual(request.call_count, 11)
            self.assertIn("Verified: 7/8", self.summary.read_text())

    def test_missing_build_cannot_report_success(self) -> None:
        with self.assertRaises(CheckError):
            check_live_site(self.output, "https://site.example/")
        with self.assertRaises(CheckError):
            external_links(self.output, "https://site.example/")

    def test_remote_checks_require_https_but_local_preview_is_allowed(self) -> None:
        self.assertEqual(site_base("http://127.0.0.1:8000"), "http://127.0.0.1:8000/")
        for value in ("http://site.example/", "https://user:secret@site.example/",
                      "https://site.example/?query=1", "https://site.example/#fragment"):
            with self.subTest(value=value), self.assertRaises(CheckError):
                site_base(value)
