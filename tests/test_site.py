"""End-to-end checks for content, generated HTML and the Pages artifact."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

from portfolio_site.brand import (
    BRAND_LEFT,
    BRAND_RIGHT,
    BRAND_TOP,
    BRAND_VOID,
    favicon_svg,
    social_card_svg,
)
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
        self.buttons: list[dict[str, str]] = []
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
        if tag == "button":
            self.buttons.append(attributes)
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


def parse_structured_data(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    opening = '<script type="application/ld+json">'
    payload = source.split(opening, 1)[1].split("</script>", 1)[0]
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise AssertionError("JSON-LD document must be an object")
    return document


class ContentTests(unittest.TestCase):
    def test_profile_is_valid_and_complete(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        self.assertEqual(profile.site.name, "Marcin Cuber")
        self.assertEqual(profile.site.last_updated, "2026-09-04")
        self.assertGreaterEqual(len(profile.projects), 6)
        self.assertGreaterEqual(len(profile.articles), 4)
        self.assertGreaterEqual(len(profile.career), 6)
        self.assertGreaterEqual(len(profile.site.cv_profile), 2)
        self.assertGreaterEqual(len(profile.open_source_organisations), 1)
        self.assertEqual(profile.site.avatar_asset, "personal-photo.png")
        self.assertEqual(profile.site.github_avatar_asset, "github-profile.jpg")
        self.assertEqual(profile.community_callout.action, "Join the journey")
        self.assertEqual(
            profile.community_callout.url,
            "https://paypal.me/marcincube",
        )
        self.assertEqual(
            profile.site.consulting_availability,
            "Remote-first or hybrid · maximum one office day per week",
        )
        self.assertEqual(sum(entry.current for entry in profile.career), 1)

    def test_native_cube_catalogue_contains_all_six_modules(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        native_cube = next(
            organisation
            for organisation in profile.open_source_organisations
            if organisation.name == "Native Cube"
        )

        self.assertEqual(native_cube.url, "https://github.com/native-cube")
        self.assertEqual(native_cube.website_url, "https://native-cube.com/")
        self.assertEqual(
            native_cube.registry_url,
            "https://registry.terraform.io/namespaces/native-cube",
        )
        self.assertEqual(
            tuple(tool.name for tool in native_cube.tools),
            (
                "Kubernetes Manifest Builder",
                "Helm Chart Builder",
                "Kubernetes RBAC Explorer",
                "Visual Subnet Calculator",
                "YAML & JSON Formatter",
            ),
        )
        self.assertEqual(
            tuple(tool.url for tool in native_cube.tools),
            (
                "https://native-cube.com/k8s-manifest-builder/",
                "https://native-cube.com/helm-chart-builder/",
                "https://native-cube.com/kubernetes-rbac-explorer/",
                "https://native-cube.com/visual-subnet-calculator/",
                "https://native-cube.com/yaml-formatter/",
            ),
        )
        self.assertEqual(
            tuple(module.repository for module in native_cube.modules),
            (
                "terraform-aws-eks",
                "terraform-aws-eks-auto",
                "terraform-aws-eks-node-group",
                "terraform-aws-eks-fargate-profile",
                "terraform-aws-kms",
                "terraform-aws-vpc-flow-logs",
            ),
        )
        self.assertEqual(len({module.url for module in native_cube.modules}), 6)

    def test_duplicate_projects_are_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["projects"].append(dict(data["projects"][0]))
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "duplicate project repository"):
                Profile.load(invalid)

    def test_duplicate_open_source_module_urls_are_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        modules = data["open_source_organisations"][0]["modules"]
        modules.append(dict(modules[0]))
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "duplicate open-source module URL"):
                Profile.load(invalid)

    def test_duplicate_open_source_tool_urls_are_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        tools = data["open_source_organisations"][0]["tools"]
        tools.append(dict(tools[0]))
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "duplicate open-source tool URL"):
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

    def test_unsafe_avatar_asset_name_is_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["site"]["avatar_asset"] = "../personal-photo.png"
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "local asset filename"):
                Profile.load(invalid)

    def test_invalid_site_last_updated_date_is_rejected(self) -> None:
        source = PROJECT_ROOT / "content" / "profile.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["site"]["last_updated"] = "30 July 2026"
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "profile.json"
            invalid.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ContentError, "must use YYYY-MM-DD"):
                Profile.load(invalid)


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.result = build_site(Path(cls.temporary.name) / "site")
        cls.output = cls.result.output
        cls.html_files = tuple(sorted(cls.output.rglob("*.html")))
        cls.parsers = {path: parse_document(path) for path in cls.html_files}
        cls.materialised = {
            path.relative_to(cls.output).as_posix() for path in cls.result.files
        }
        cls.favicon_asset = next(
            name
            for name in cls.materialised
            if name.startswith("assets/favicon.") and name.endswith(".svg")
        )
        cls.social_card_asset = next(
            name
            for name in cls.materialised
            if name.startswith("assets/social-card.") and name.endswith(".svg")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_expected_pages_and_metadata_exist(self) -> None:
        expected = {
            "index.html",
            "cv/index.html",
            "404.html",
            "cv/Marcin-Cuber-CV.pdf",
            "robots.txt",
            "sitemap.xml",
            "site.webmanifest",
            ".nojekyll",
        }
        materialised = self.materialised
        self.assertTrue(expected.issubset(materialised))
        self.assertIn(self.favicon_asset, materialised)
        self.assertIn(self.social_card_asset, materialised)
        self.assertTrue(any(name.startswith("assets/styles.") for name in materialised))
        self.assertTrue(any(name.startswith("assets/site.") for name in materialised))
        self.assertTrue(
            any(
                name.startswith("assets/personal-photo.") and name.endswith(".png")
                for name in materialised
            )
        )
        self.assertTrue(
            any(
                name.startswith("assets/github-profile.") and name.endswith(".jpg")
                for name in materialised
            )
        )
        self.assertFalse(any(name.startswith("legacy/") for name in materialised))

    def test_cv_pdf_is_a_direct_progressive_download(self) -> None:
        cv_path = self.output / "cv" / "index.html"
        cv = cv_path.read_text(encoding="utf-8")
        parser = self.parsers[cv_path]
        download_links = [
            link
            for link in parser.links
            if link.get("class") == "button button--dark cv-pdf-download"
        ]

        self.assertEqual(len(download_links), 1)
        self.assertEqual(download_links[0].get("href"), "Marcin-Cuber-CV.pdf")
        self.assertEqual(download_links[0].get("download"), "Marcin-Cuber-CV.pdf")
        self.assertEqual(download_links[0].get("type"), "application/pdf")
        self.assertNotIn("target", download_links[0])
        self.assertIn(">Save PDF</a>", cv)
        self.assertNotIn("Print / save PDF", cv)
        self.assertNotIn("data-print", cv)

        pdf = (self.output / "cv" / "Marcin-Cuber-CV.pdf").read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreater(len(pdf), 100_000)

        script = (PROJECT_ROOT / "static" / "site.js").read_text(encoding="utf-8")
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("window.print()", script)
        self.assertNotIn("[data-print]", script)
        self.assertIn(".cv-pdf-download,", styles)

    def test_cube_r_identity_replaces_the_legacy_mc_mark(self) -> None:
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        cv = (self.output / "cv" / "index.html").read_text(encoding="utf-8")
        not_found = (self.output / "404.html").read_text(encoding="utf-8")
        favicon = (self.output / self.favicon_asset).read_text(
            encoding="utf-8"
        )
        social_card = (self.output / self.social_card_asset).read_text(
            encoding="utf-8"
        )

        for source, expected_marks in (
            (homepage, 2),
            (cv, 1),
            (not_found, 1),
        ):
            self.assertEqual(source.count('class="brand-mark"'), expected_marks)
            self.assertNotIn(">MC<", source)
            self.assertIn('aria-label="Marcin Cuber — home"', source)
        self.assertIn("Cuber cube-R identity mark", favicon)
        self.assertIn("registered-style R roundel", favicon)
        self.assertIn('d="M32 9 50 19 32 29 14 19 32 9Z"', favicon)
        self.assertIn(f'fill="{BRAND_TOP}"', favicon)
        self.assertIn(f'fill="{BRAND_LEFT}"', favicon)
        self.assertIn(f'fill="{BRAND_RIGHT}"', favicon)
        self.assertNotIn('aria-label="MC"', favicon)
        self.assertNotIn(">MC<", social_card)
        ET.fromstring(favicon)
        ET.fromstring(social_card)
        self.assertEqual(favicon, f"{favicon_svg()}\n")
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        self.assertEqual(
            social_card,
            (
                social_card_svg(
                    name=profile.site.name,
                    role=profile.site.role,
                    short_role=profile.site.short_role,
                    description=profile.site.description,
                    focus_line=" · ".join(
                        item.title for item in profile.expertise[:3]
                    ),
                    location=profile.site.location,
                    canonical_url=profile.site.canonical_url,
                )
                + "\n"
            ),
        )

        manifest = json.loads(
            (self.output / "site.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["icons"][0]["src"], f"/{self.favicon_asset}")
        self.assertEqual(manifest["id"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["lang"], "en-GB")
        self.assertTrue(manifest["description"])
        self.assertEqual(manifest["background_color"], BRAND_VOID)
        self.assertEqual(manifest["theme_color"], BRAND_VOID)
        social_url = f"https://marcincuber.github.io/{self.social_card_asset}"
        for path, parser in self.parsers.items():
            with self.subTest(page=path.relative_to(self.output)):
                source = path.read_text(encoding="utf-8")
                icon_href = (
                    self.favicon_asset
                    if path == self.output / "index.html"
                    else f"../{self.favicon_asset}"
                    if path == self.output / "cv" / "index.html"
                    else self.favicon_asset
                )
                self.assertIn(
                    f'<link rel="icon" href="{icon_href}" type="image/svg+xml">',
                    source,
                )
                self.assertIn(
                    {
                        "property": "og:image",
                        "content": social_url,
                    },
                    parser.meta,
                )
                self.assertIn(
                    {
                        "name": "twitter:image",
                        "content": social_url,
                    },
                    parser.meta,
                )
                self.assertIn(
                    {
                        "name": "theme-color",
                        "content": BRAND_VOID,
                    },
                    parser.meta,
                )

    def test_search_metadata_is_specific_complete_and_crawlable(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        cv = (self.output / "cv" / "index.html").read_text(encoding="utf-8")
        not_found = (self.output / "404.html").read_text(encoding="utf-8")
        index_directive = (
            "index, follow, max-image-preview:large, "
            "max-snippet:-1, max-video-preview:-1"
        )

        for path, expected_robots, expected_og_type in (
            (self.output / "index.html", index_directive, "profile"),
            (self.output / "cv" / "index.html", index_directive, "profile"),
            (self.output / "404.html", "noindex, follow", "website"),
        ):
            with self.subTest(page=path.relative_to(self.output)):
                parser = self.parsers[path]
                self.assertIn(
                    {"name": "robots", "content": expected_robots},
                    parser.meta,
                )
                self.assertIn(
                    {"property": "og:type", "content": expected_og_type},
                    parser.meta,
                )
                self.assertIn(
                    {"property": "og:locale", "content": "en_GB"},
                    parser.meta,
                )
                self.assertIn(
                    {"property": "og:site_name", "content": profile.site.name},
                    parser.meta,
                )
                self.assertIn(
                    {"property": "og:image:width", "content": "1200"},
                    parser.meta,
                )
                self.assertIn(
                    {"property": "og:image:height", "content": "630"},
                    parser.meta,
                )
                twitter_alt = [
                    item
                    for item in parser.meta
                    if item.get("name") == "twitter:image:alt"
                ]
                self.assertEqual(len(twitter_alt), 1)
                self.assertTrue(twitter_alt[0].get("content"))

        self.assertIn(
            f"<title>{escape(profile.site.name)} CV — "
            f"{escape(profile.site.short_role)}</title>",
            cv,
        )
        for social in profile.socials:
            self.assertIn(
                f'<link rel="me" href="{escape(social.url, quote=True)}">',
                homepage,
            )
        self.assertIn('property="profile:first_name" content="Marcin"', homepage)
        self.assertIn('property="profile:last_name" content="Cuber"', cv)
        self.assertNotIn('property="profile:first_name"', not_found)

    def test_structured_data_describes_site_person_and_visible_activity(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        homepage_data = parse_structured_data(self.output / "index.html")
        homepage_graph = homepage_data["@graph"]
        self.assertIsInstance(homepage_graph, list)
        homepage_by_type = {item["@type"]: item for item in homepage_graph}

        website = homepage_by_type["WebSite"]
        self.assertEqual(website["name"], profile.site.name)
        self.assertEqual(website["url"], f"{profile.site.canonical_url}/")
        self.assertIn("marcincuber.github.io", website["alternateName"])

        person = homepage_by_type["Person"]
        self.assertEqual(person["description"], profile.site.description)
        self.assertEqual(
            person["sameAs"],
            [social.url for social in profile.socials],
        )
        self.assertEqual(person["worksFor"]["name"], "Capgemini")
        self.assertEqual(person["affiliation"][0]["name"], "Native Cube")
        self.assertEqual(
            len(person["hasCredential"]),
            len(profile.certifications),
        )

        profile_page = homepage_by_type["ProfilePage"]
        self.assertEqual(profile_page["dateModified"], profile.site.last_updated)
        self.assertEqual(
            profile_page["mainEntity"]["@id"],
            f"{profile.site.canonical_url}/#person",
        )
        self.assertEqual(
            [item["url"] for item in profile_page["hasPart"]],
            [article.url for article in profile.articles],
        )
        self.assertEqual(
            [item["datePublished"] for item in profile_page["hasPart"]],
            [article.date for article in profile.articles],
        )

        cv_data = parse_structured_data(self.output / "cv" / "index.html")
        cv_graph = cv_data["@graph"]
        self.assertEqual(
            {item["@type"] for item in cv_graph},
            {"Person", "ProfilePage"},
        )
        cv_page = next(item for item in cv_graph if item["@type"] == "ProfilePage")
        self.assertNotIn("hasPart", cv_page)
        self.assertEqual(
            cv_page["name"],
            f"{profile.site.name} CV — {profile.site.short_role}",
        )

        not_found_data = parse_structured_data(self.output / "404.html")
        self.assertEqual(
            [item["@type"] for item in not_found_data["@graph"]],
            ["WebPage"],
        )

    def test_profile_images_are_fingerprinted_and_used_for_distinct_roles(self) -> None:
        materialised = {
            path.relative_to(self.output).as_posix() for path in self.result.files
        }
        avatar_asset = next(
            name
            for name in materialised
            if name.startswith("assets/personal-photo.") and name.endswith(".png")
        )
        github_avatar_asset = next(
            name
            for name in materialised
            if name.startswith("assets/github-profile.") and name.endswith(".jpg")
        )
        homepage = (self.output / "index.html").read_text(encoding="utf-8")

        self.assertIn(f'src="{avatar_asset}"', homepage)
        self.assertIn('alt="Portrait of Marcin Cuber"', homepage)
        self.assertIn(f'src="{github_avatar_asset}"', homepage)
        self.assertIn("alt=\"Marcin Cuber’s GitHub avatar\"", homepage)
        self.assertIn('class="console-link console-link--github"', homepage)
        self.assertIn(
            f'"image":"https://marcincuber.github.io/{avatar_asset}"',
            homepage,
        )

    def test_hero_console_is_left_and_availability_links_to_linkedin(self) -> None:
        parser = self.parsers[self.output / "index.html"]
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        linkedin = next(
            social for social in profile.socials if social.label == "LinkedIn"
        )
        availability_links = [
            link for link in parser.links if link.get("class") == "availability"
        ]
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        homepage = (self.output / "index.html").read_text(encoding="utf-8")

        self.assertEqual(len(availability_links), 1)
        self.assertEqual(availability_links[0].get("href"), linkedin.url)
        self.assertEqual(availability_links[0].get("target"), "_blank")
        self.assertIn("noopener", availability_links[0].get("rel", ""))
        self.assertIn('grid-template-areas: "console copy"', styles)
        self.assertIn("grid-area: console", styles)
        self.assertIn("grid-area: copy", styles)
        self.assertIn("font-size: clamp(3.1rem, 5.6vw, 5.75rem)", styles)
        self.assertIn('class="yaml-list__consulting"', homepage)
        self.assertIn(
            escape(profile.site.consulting_availability),
            homepage,
        )
        self.assertNotIn("consulting-availability__status", homepage)

    def test_portrait_lightbox_is_progressive_and_accessible(self) -> None:
        materialised = {
            path.relative_to(self.output).as_posix() for path in self.result.files
        }
        avatar_asset = next(
            name
            for name in materialised
            if name.startswith("assets/personal-photo.") and name.endswith(".png")
        )
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        parser = self.parsers[self.output / "index.html"]
        close_buttons = [
            button for button in parser.buttons if "data-portrait-close" in button
        ]

        self.assertIn(
            f'class="profile-photo-trigger" href="{avatar_asset}"',
            homepage,
        )
        self.assertIn("data-portrait-open", homepage)
        self.assertIn('aria-controls="portrait-dialog"', homepage)
        self.assertIn(
            'class="portrait-dialog" id="portrait-dialog" data-portrait-dialog',
            homepage,
        )
        self.assertIn('aria-labelledby="portrait-dialog-title"', homepage)
        self.assertIn('id="portrait-dialog-title"', homepage)
        self.assertEqual(homepage.count(f'src="{avatar_asset}"'), 2)
        self.assertEqual(len(close_buttons), 1)
        self.assertEqual(close_buttons[0].get("type"), "button")
        self.assertEqual(
            close_buttons[0].get("aria-label"),
            "Close enlarged portrait",
        )

        script = (PROJECT_ROOT / "static" / "site.js").read_text(encoding="utf-8")
        self.assertIn("portraitDialog.showModal()", script)
        self.assertIn('portraitDialog.addEventListener("cancel"', script)
        self.assertIn("portraitTrigger.focus({ preventScroll: true })", script)
        self.assertIn("event.target === portraitDialog", script)

        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (hover: hover) and (pointer: fine)", styles)
        self.assertIn(".profile-photo-trigger:hover", styles)
        self.assertIn(".portrait-dialog::backdrop", styles)

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

    def test_cv_uses_a_dedicated_multi_paragraph_profile(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        cv_source = (self.output / "cv" / "index.html").read_text(encoding="utf-8")
        homepage_source = (self.output / "index.html").read_text(encoding="utf-8")

        self.assertIn('class="cv-summary-copy"', cv_source)
        self.assertEqual(
            cv_source.count('class="cv-profile-paragraph"'),
            len(profile.site.cv_profile),
        )
        for paragraph in profile.site.cv_profile:
            self.assertIn(escape(paragraph), cv_source)
            self.assertNotIn(escape(paragraph), homepage_source)

    def test_open_source_organisations_are_rendered_on_homepage_and_cv(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        cv = (self.output / "cv" / "index.html").read_text(encoding="utf-8")

        self.assertEqual(
            homepage.count('class="organisation-card"'),
            len(profile.open_source_organisations),
        )
        self.assertEqual(
            cv.count('class="cv-organisation"'),
            len(profile.open_source_organisations),
        )
        self.assertLess(
            homepage.index('class="organisation-grid"'),
            homepage.index('class="project-grid"'),
        )
        for organisation in profile.open_source_organisations:
            self.assertIn(escape(organisation.name), homepage)
            self.assertIn(escape(organisation.name), cv)
            self.assertIn(escape(organisation.evidence), homepage)
            self.assertIn(escape(organisation.website_url, quote=True), homepage)
            self.assertIn(escape(organisation.url, quote=True), homepage)
            self.assertIn(escape(organisation.registry_url, quote=True), homepage)
            self.assertIn(escape(organisation.website_url, quote=True), cv)
            for tool in organisation.tools:
                self.assertIn(escape(tool.name), homepage)
                self.assertIn(escape(tool.url, quote=True), homepage)
            for module in organisation.modules:
                self.assertIn(escape(module.repository), homepage)
                self.assertIn(escape(module.summary), homepage)
                self.assertIn(escape(module.url, quote=True), homepage)

    def test_cv_presents_open_source_organisation_as_a_single_site_summary(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        cv = (self.output / "cv" / "index.html").read_text(encoding="utf-8")
        section = cv.split(
            '<section class="cv-section" '
            'aria-labelledby="open-source-organisations-heading">',
            1,
        )[1].split("</section>", 1)[0]
        native_cube = next(
            organisation
            for organisation in profile.open_source_organisations
            if organisation.name == "Native Cube"
        )

        self.assertIn(
            '<a class="cv-organisation__website" '
            f'href="{escape(native_cube.website_url, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">native-cube.com',
            section,
        )
        self.assertIn(escape(native_cube.summary), section)
        self.assertNotIn(escape(native_cube.handle), section)
        self.assertNotIn(escape(native_cube.evidence), section)
        self.assertNotIn(escape(native_cube.url, quote=True), section)
        self.assertNotIn(escape(native_cube.registry_url, quote=True), section)
        self.assertNotIn("tools ·", section)
        self.assertNotIn("Product owned by me", section)
        self.assertNotIn('class="cv-organisation__ownership"', section)

    def test_cv_print_css_uses_balanced_a4_columns_and_safe_breaks(self) -> None:
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "grid-template-columns: minmax(0, 1.7fr) minmax(48mm, 0.8fr);",
            styles,
        )
        self.assertIn(".cv-sidebar {\n    display: block;\n  }", styles)
        self.assertIn("gap: 6mm;", styles)
        self.assertIn("font-size: 7.8pt;", styles)
        self.assertIn("break-inside: auto;", styles)
        self.assertIn("break-after: avoid;", styles)

    def test_native_cube_title_links_to_website_and_uses_brand_logo(self) -> None:
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        parser = self.parsers[self.output / "index.html"]
        title_links = [
            link
            for link in parser.links
            if link.get("class") == "organisation-card__title-link"
        ]

        self.assertEqual(len(title_links), 1)
        self.assertEqual(title_links[0].get("href"), "https://native-cube.com/")
        self.assertEqual(title_links[0].get("target"), "_blank")
        self.assertIn("noopener", title_links[0].get("rel", ""))
        self.assertIn('class="organisation-card__logo"', homepage)
        self.assertIn(
            'd="M20 2.5 36 11.3 20 20 4 11.3 20 2.5Z" fill="#2563eb"',
            homepage,
        )
        self.assertNotIn(
            'class="organisation-card__mark" aria-hidden="true">NC</span>',
            homepage,
        )

    def test_native_cube_website_is_linked_from_every_primary_navigation(self) -> None:
        for path, parser in self.parsers.items():
            with self.subTest(page=path.relative_to(self.output)):
                native_cube_links = [
                    link
                    for link in parser.links
                    if link.get("aria-label")
                    == "Native Cube — opens in a new tab"
                ]

                self.assertEqual(len(native_cube_links), 1)
                self.assertEqual(
                    native_cube_links[0].get("href"), "https://native-cube.com/"
                )
                self.assertEqual(native_cube_links[0].get("target"), "_blank")
                self.assertIn("noopener", native_cube_links[0].get("rel", ""))

    def test_primary_navigation_has_a_clear_internal_to_external_order(self) -> None:
        expected_labels = (
            ">Work</a>",
            ">Expertise</a>",
            ">Writing</a>",
            ">Journey</a>",
            ">CV</a>",
            ">Native Cube <span",
        )
        for path in self.parsers:
            with self.subTest(page=path.relative_to(self.output)):
                source = path.read_text(encoding="utf-8")
                navigation = source.split(
                    '<nav class="site-nav" id="site-navigation"', 1
                )[1].split("</nav>", 1)[0]
                positions = [navigation.index(label) for label in expected_labels]

                self.assertEqual(positions, sorted(positions))
                self.assertIn('class="nav-external-item"', navigation)

    def test_join_the_journey_callout_closes_the_homepage(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        homepage_path = self.output / "index.html"
        homepage = homepage_path.read_text(encoding="utf-8")
        parser = self.parsers[homepage_path]
        callout = profile.community_callout
        journey_links = [
            link
            for link in parser.links
            if "button--journey" in link.get("class", "").split()
        ]

        self.assertIn(escape(callout.title), homepage)
        self.assertIn(escape(callout.message), homepage)
        self.assertEqual(len(journey_links), 1)
        self.assertEqual(journey_links[0].get("href"), callout.url)
        self.assertEqual(journey_links[0].get("target"), "_blank")
        self.assertIn("noopener", journey_links[0].get("rel", ""))
        self.assertLess(
            homepage.index('class="contact-section"'),
            homepage.index('class="journey-support"'),
        )
        self.assertLess(
            homepage.index('class="journey-support"'),
            homepage.index('class="site-footer"'),
        )

    def test_join_the_journey_button_is_in_every_header(self) -> None:
        profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        for path, parser in self.parsers.items():
            with self.subTest(page=path.relative_to(self.output)):
                header_links = [
                    link
                    for link in parser.links
                    if "header-journey-link" in link.get("class", "").split()
                ]

                self.assertEqual(len(header_links), 1)
                self.assertEqual(
                    header_links[0].get("href"),
                    profile.community_callout.url,
                )
                self.assertEqual(header_links[0].get("target"), "_blank")
                self.assertIn("noopener", header_links[0].get("rel", ""))

    def test_section_progress_rail_has_cross_browser_svg_and_scroll_fallback(self) -> None:
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        script = (PROJECT_ROOT / "static" / "site.js").read_text(
            encoding="utf-8"
        )

        self.assertEqual(homepage.count('class="section-rail__tick"'), 4)
        self.assertEqual(homepage.count('data-rail-link'), 4)
        self.assertIn(
            'aria-label="Page progress and section navigation"',
            homepage,
        )
        self.assertIn("@media (min-width: 64rem)", styles)
        self.assertNotIn("@media (min-width: 96rem)", styles)
        self.assertIn("-webkit-backdrop-filter: blur(10px);", styles)
        self.assertIn("if (railLinks.length) {", script)
        self.assertIn("getBoundingClientRect()", script)
        self.assertIn('window.addEventListener("scroll", requestRailUpdate', script)

    def test_theme_switcher_defaults_to_current_theme(self) -> None:
        for path, parser in self.parsers.items():
            with self.subTest(page=path.relative_to(self.output)):
                source = path.read_text(encoding="utf-8")
                theme_toggles = [
                    button for button in parser.buttons if "data-theme-toggle" in button
                ]

                self.assertEqual(parser.html_attributes.get("data-theme"), "light")
                self.assertEqual(len(theme_toggles), 1)
                self.assertEqual(theme_toggles[0].get("aria-pressed"), "false")
                self.assertIn('localStorage.getItem("mc-theme")', source)
                self.assertLess(
                    source.index('localStorage.getItem("mc-theme")'),
                    source.index('<link rel="stylesheet"'),
                )

        script = (PROJECT_ROOT / "static" / "site.js").read_text(encoding="utf-8")
        self.assertIn('localStorage.setItem(THEME_STORAGE_KEY, selectedTheme)', script)
        self.assertIn('navigation.querySelector("a")?.focus()', script)
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('html[data-theme="dark"]', styles)

    def test_cube_r_theme_has_accessible_visual_fallbacks(self) -> None:
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        cv = (self.output / "cv" / "index.html").read_text(encoding="utf-8")
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )

        for token in (
            "--cube-void:",
            "--brand-accent:",
            "--cube-top:",
            "--cube-left:",
            "--cube-right:",
            "--cube-line:",
            "--cube-glow:",
            "--cube-facet:",
            "--cube-shape:",
        ):
            self.assertIn(token, styles)
        for selector in (
            ".profile-console::before",
            ".project-card::before",
            ".project-icon span:nth-child(1)",
            ".organisation-modules a::before",
            ".section--expertise::after",
            ".architecture-label i::after",
            ".expertise-card li::before",
            ".section--impact::before",
            ".article-index",
            ".timeline-rail span",
            ".credential-count::before",
            ".contact-section::before",
        ):
            self.assertIn(selector, styles)
        self.assertIn("@media (forced-colors: active)", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)
        self.assertIn("@media print", styles)
        self.assertIn('class="project-icon" aria-hidden="true"', homepage)
        self.assertIn('class="article-index" aria-hidden="true"', homepage)
        self.assertIn(
            'class="brand-mark cv-brand-mark" viewBox="0 0 64 64" '
            'aria-hidden="true" focusable="false"',
            cv,
        )

    def test_homepage_omits_removed_build_pipeline_section(self) -> None:
        homepage = (self.output / "index.html").read_text(encoding="utf-8")
        styles = (PROJECT_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("The site is a system too", homepage)
        self.assertNotIn('class="section section--build"', homepage)
        self.assertNotIn('class="pipeline"', homepage)
        self.assertNotIn(".section--build", styles)
        self.assertNotIn(".pipeline", styles)

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
                *(image.get("src", "") for image in parser.images),
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
        modified = [
            node.text for node in document.findall("s:url/s:lastmod", namespace)
        ]
        self.assertEqual(modified, ["2026-09-04", "2026-09-04"])
        self.assertEqual(document.findall("s:url/s:priority", namespace), [])

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
