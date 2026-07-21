"""End-to-end checks for content, generated HTML and the Pages artifact."""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

from portfolio_site.builder import PROJECT_ROOT, build_site
from portfolio_site.content import ContentError, Profile


class DocumentParser(HTMLParser):
    """Collect the small amount of document structure needed by the checks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts: dict[str, int] = {}
        self.ids: set[str] = set()
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.resources: list[str] = []
        self.meta: list[dict[str, str]] = []
        self.html_attributes: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        self.counts[tag] = self.counts.get(tag, 0) + 1
        if tag == "html":
            self.html_attributes = attributes
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a":
            self.links.append(attributes)
        if tag == "img":
            self.images.append(attributes)
        if tag in {"link", "script"}:
            resource = attributes.get("href") or attributes.get("src")
            if resource:
                self.resources.append(resource)
        if tag == "meta":
            self.meta.append(attributes)


def parse_document(path: Path) -> DocumentParser:
    parser = DocumentParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


class ContentTests(unittest.TestCase):
    def test_profile_is_valid_and_complete(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        self.assertEqual(profile.site.name, "Marcin Cuber")
        self.assertGreaterEqual(len(profile.projects), 6)
        self.assertGreaterEqual(len(profile.articles), 4)
        self.assertGreaterEqual(len(profile.career), 6)
        self.assertEqual(sum(entry.current for entry in profile.career), 1)

    def test_duplicate_projects_are_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["projects"].append(dict(data["projects"][0]))
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "duplicate project repository"):
                Profile.load(invalid)

    def test_insecure_public_url_is_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["socials"][0]["url"] = "http://example.com/profile"
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "absolute HTTPS URL"):
                Profile.load(invalid)


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.result = build_site(Path(cls.temporary.name) / "site")
        cls.output = cls.result.output
        cls.html_files = tuple(sorted(cls.output.rglob("*.html")))
        cls.parsers = {path: parse_document(path) for path in cls.html_files}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_expected_pages_and_metadata_exist(self) -> None:
        expected = {
            "index.html",
            "cv/index.html",
            "404.html",
            "robots.txt",
            "sitemap.xml",
            "site.webmanifest",
            ".nojekyll",
            "assets/favicon.svg",
            "assets/social-card.svg",
        }
        materialised = {
            path.relative_to(self.output).as_posix() for path in self.result.files
        }
        self.assertTrue(expected.issubset(materialised))
        self.assertTrue(any(name.startswith("assets/styles.") for name in materialised))
        self.assertTrue(any(name.startswith("assets/site.") for name in materialised))
        self.assertFalse(any(name.startswith("legacy/") for name in materialised))

    def test_html_has_semantic_basics(self) -> None:
        for path, parser in self.parsers.items():
            with self.subTest(page=path.relative_to(self.output)):
                source = path.read_text(encoding="utf-8")
                self.assertTrue(source.lower().startswith("<!doctype html>"))
                self.assertEqual(parser.html_attributes.get("lang"), "en-GB")
                self.assertEqual(parser.counts.get("title"), 1)
                self.assertEqual(parser.counts.get("h1"), 1)
                self.assertEqual(parser.counts.get("main"), 1)
                self.assertIn('type="application/ld+json"', source)
                self.assertNotIn("$page_title", source)
                descriptions = [item for item in parser.meta if item.get("name") == "description"]
                self.assertEqual(len(descriptions), 1)
                self.assertTrue(descriptions[0].get("content"))

    def test_education_and_certifications_are_grouped_into_two_panels(self) -> None:
        source = (self.output / "index.html").read_text(encoding="utf-8")
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")

        self.assertEqual(source.count('<section class="credential-panel '), 2)
        self.assertIn("credential-panel--education", source)
        self.assertIn("credential-panel--certifications", source)
        self.assertEqual(source.count('class="education-item"'), len(profile.education))
        self.assertEqual(
            source.count('class="certification-item"'), len(profile.certifications)
        )

    def test_images_have_accessible_dimensions(self) -> None:
        for path, parser in self.parsers.items():
            for image in parser.images:
                with self.subTest(page=path.name, image=image.get("src")):
                    self.assertTrue(image.get("alt"))
                    self.assertTrue(image.get("width"))
                    self.assertTrue(image.get("height"))

    def test_new_tab_links_are_hardened(self) -> None:
        for path, parser in self.parsers.items():
            for link in parser.links:
                if link.get("target") != "_blank":
                    continue
                with self.subTest(page=path.name, href=link.get("href")):
                    rel = set(link.get("rel", "").split())
                    self.assertIn("noopener", rel)
                    self.assertIn("noreferrer", rel)

    def test_internal_links_assets_and_fragments_resolve(self) -> None:
        parsed_by_relative = {
            path.relative_to(self.output).as_posix(): parser
            for path, parser in self.parsers.items()
        }
        for page, parser in self.parsers.items():
            relative_page = page.relative_to(self.output).as_posix()
            base_url = "/" + relative_page
            for reference in [
                *(link.get("href", "") for link in parser.links),
                *parser.resources,
            ]:
                if not reference or reference.startswith(("https://", "mailto:", "data:")):
                    continue
                with self.subTest(page=relative_page, reference=reference):
                    resolved = urlsplit(urljoin(base_url, reference))
                    target_name = resolved.path.lstrip("/")
                    if not target_name or target_name.endswith("/"):
                        target_name += "index.html"
                    target = self.output / target_name
                    self.assertTrue(target.is_file(), f"missing internal target: {target_name}")
                    if resolved.fragment and target_name.endswith(".html"):
                        target_parser = parsed_by_relative[target_name]
                        self.assertIn(
                            resolved.fragment,
                            target_parser.ids,
                            f"missing #{resolved.fragment} in {target_name}",
                        )

    def test_asset_names_match_their_sha256_digest(self) -> None:
        for path in (self.output / "assets").iterdir():
            parts = path.name.split(".")
            if len(parts) != 3 or parts[1] in {"card"}:
                continue
            digest = sha256(path.read_bytes()).hexdigest()[:12]
            self.assertEqual(parts[1], digest)

    def test_sitemap_is_well_formed_and_canonical(self) -> None:
        document = ET.parse(self.output / "sitemap.xml")
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in document.findall("s:url/s:loc", namespace)]
        self.assertEqual(
            locations,
            ["https://marcincuber.github.io/", "https://marcincuber.github.io/cv/"],
        )

    def test_build_is_content_deterministic(self) -> None:
        second = Path(self.temporary.name) / "site-two"
        build_site(second)
        first_files = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second).as_posix(): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)

    def test_builder_refuses_to_replace_project_root(self) -> None:
        with self.assertRaisesRegex(ContentError, "unsafe build output"):
            build_site(PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
