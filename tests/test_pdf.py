"""Structural and content checks for the generated CV PDF."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import unittest

from portfolio_site.content import Profile
from portfolio_site.pdf import PdfRenderError, render_cv_pdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = Profile.load(PROJECT_ROOT / "content" / "profile.json")
        cls.pdf = render_cv_pdf(cls.profile)

    def test_pdf_has_a4_pages_searchable_text_and_unicode_metadata(self) -> None:
        pdf = self.pdf
        profile = self.profile

        self.assertTrue(pdf.startswith(b"%PDF-1.4\n"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertEqual(pdf.count(b"/Type /Page "), 2)
        self.assertEqual(pdf.count(b"/MediaBox [0 0 595.28 841.89]"), 2)
        self.assertEqual(
            pdf.count(b"q 1 1 1 rg 0 0 595.28 841.89 re f Q"),
            2,
        )
        self.assertEqual(pdf.count(b"/ToUnicode "), 2)
        self.assertIn(b"<95> <2022>", pdf)
        self.assertIn(b"<97> <2014>", pdf)

        title = re.search(rb"/Title <([0-9A-F]+)>", pdf)
        if title is None:
            self.fail("PDF Info dictionary is missing its Unicode title")
        decoded_title = bytes.fromhex(title.group(1).decode("ascii")).decode("utf-16")
        self.assertEqual(
            decoded_title,
            f"{profile.site.name} CV — {profile.site.short_role}",
        )

        for expected_text in (b"Marcin Cuber", b"Capgemini", b"Native Cube"):
            self.assertIn(expected_text, pdf)
        native_cube = profile.open_source_organisations[0]
        for summary_fragment in (
            b"I own Native Cube, a collection of free browser",
            b"tools for Kubernetes, Helm, RBAC, subnet",
            b"planning and YAML/JSON, alongside reusable",
            b"AWS Terraform modules.",
        ):
            self.assertIn(summary_fragment, pdf)
        self.assertNotIn(native_cube.handle.encode("ascii"), pdf)
        self.assertNotIn(native_cube.evidence.encode("ascii"), pdf)
        self.assertNotIn(b"Product owned by me", pdf)

    def test_pdf_links_are_safe_and_connected_to_the_structure_tree(self) -> None:
        pdf = self.pdf
        profile = self.profile

        self.assertIn(b"/MarkInfo << /Marked true >>", pdf)
        self.assertIn(b"/Lang (en-GB)", pdf)
        self.assertIn(b"/DisplayDocTitle true", pdf)
        self.assertEqual(pdf.count(b"/Tabs /S"), 2)
        self.assertEqual(pdf.count(b"/S /Document "), 1)
        self.assertEqual(pdf.count(b"/S /H1 "), 1)

        annotation_count = pdf.count(b"/Type /Annot ")
        self.assertGreater(annotation_count, 1)
        self.assertEqual(pdf.count(b"/StructParent "), annotation_count)
        self.assertEqual(pdf.count(b"/Type /OBJR "), annotation_count)
        self.assertEqual(pdf.count(b"/Contents <FEFF"), annotation_count)
        self.assertEqual(
            pdf.count(b"/Type /Annot /Subtype /Link /F 4 /H /I /P "),
            annotation_count,
        )

        annotation_ids = {
            int(value)
            for value in re.findall(rb"(\d+) 0 obj\n<< /Type /Annot ", pdf)
        }
        object_reference_ids = {
            int(value)
            for value in re.findall(rb"/Type /OBJR [^>]+ /Obj (\d+) 0 R", pdf)
        }
        self.assertEqual(object_reference_ids, annotation_ids)

        parent_tree = re.search(rb"<< /Nums \[(.*?)\] >>", pdf, re.DOTALL)
        if parent_tree is None:
            self.fail("tagged PDF is missing its ParentTree number tree")
        parent_keys = {
            int(value) for value in re.findall(rb"/StructParent (\d+)", pdf)
        }
        for parent_key in parent_keys:
            self.assertRegex(
                parent_tree.group(1),
                rb"(?:^| )" + str(parent_key).encode("ascii") + rb" \d+ 0 R",
            )

        uri_values = re.findall(rb"/URI \(([^)]*)\)", pdf)
        self.assertEqual(len(uri_values), annotation_count)
        self.assertTrue(all(value.startswith(b"https://") for value in uri_values))
        expected_urls = {
            f"{profile.site.canonical_url}/cv/",
            *(social.url for social in profile.socials),
            *(
                organisation.website_url
                for organisation in profile.open_source_organisations
            ),
            *(project.url for project in profile.projects[:4]),
            *(item.url for item in profile.recognition),
        }
        self.assertEqual({value.decode("ascii") for value in uri_values}, expected_urls)

        for unsafe_feature in (
            b"/JavaScript",
            b"/Launch",
            b"/OpenAction",
            b"/EmbeddedFile",
            b"/CreationDate",
            b"/ModDate",
        ):
            self.assertNotIn(unsafe_feature, pdf)

    def test_pdf_cross_reference_table_and_stream_lengths_are_valid(self) -> None:
        pdf = self.pdf
        startxref = re.search(rb"startxref\n(\d+)\n%%EOF\n?$", pdf)
        if startxref is None:
            self.fail("PDF is missing a valid startxref trailer")
        xref_offset = int(startxref.group(1))
        self.assertEqual(pdf[xref_offset : xref_offset + 5], b"xref\n")

        xref_lines = pdf[xref_offset:].splitlines()
        first_object, object_count = map(int, xref_lines[1].split())
        self.assertEqual(first_object, 0)
        self.assertEqual(xref_lines[2], b"0000000000 65535 f ")
        in_use_rows = xref_lines[3 : 2 + object_count]
        self.assertEqual(len(in_use_rows), object_count - 1)
        for identifier, row in enumerate(in_use_rows, start=1):
            offset = int(row[:10])
            self.assertEqual(row[17:18], b"n")
            self.assertTrue(
                pdf[offset:].startswith(f"{identifier} 0 obj\n".encode("ascii")),
                f"xref entry {identifier} points to the wrong byte offset",
            )

        trailer = pdf[xref_offset:]
        self.assertIn(f"/Size {object_count}".encode("ascii"), trailer)
        object_ids = set(range(1, object_count))
        referenced_ids = {
            int(value) for value in re.findall(rb"\b(\d+) 0 R\b", pdf)
        }
        self.assertTrue(referenced_ids.issubset(object_ids))
        self.assertRegex(trailer, rb"/Root \d+ 0 R")
        self.assertRegex(trailer, rb"/Info \d+ 0 R")

        streams = tuple(re.finditer(rb"<< /Length (\d+) >>\nstream\n", pdf))
        self.assertEqual(len(streams), 3)
        for stream in streams:
            payload_start = stream.end()
            payload_end = pdf.index(b"\nendstream", payload_start)
            self.assertEqual(payload_end - payload_start, int(stream.group(1)))

    def test_generation_is_deterministic(self) -> None:
        self.assertEqual(self.pdf, render_cv_pdf(self.profile))

    def test_lossy_character_conversion_is_rejected(self) -> None:
        unsupported_site = replace(
            self.profile.site,
            role=f"{self.profile.site.role} 🚀",
        )
        unsupported_profile = replace(self.profile, site=unsupported_site)

        with self.assertRaisesRegex(PdfRenderError, r"U\+1F680"):
            render_cv_pdf(unsupported_profile)

    def test_content_that_would_be_clipped_is_rejected(self) -> None:
        oversized_entry = replace(
            self.profile.career[0],
            summary="Expanded platform delivery detail. " * 200,
        )
        oversized_profile = replace(
            self.profile,
            career=(oversized_entry, *self.profile.career[1:]),
        )

        with self.assertRaisesRegex(PdfRenderError, "exceeds the page in experience"):
            render_cv_pdf(oversized_profile)


if __name__ == "__main__":
    unittest.main()
