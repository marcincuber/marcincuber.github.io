"""Deterministic, dependency-free PDF rendering for the downloadable CV.

The site is deployed as static files, so the CV PDF has to exist at build time.
Generating it directly from :class:`Profile` keeps the download aligned with the
HTML CV without committing a derived binary to the repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import unicodedata

from .content import CareerEntry, ContentError, Education, Expertise, Profile


A4_WIDTH = 595.28
A4_HEIGHT = 841.89
MARGIN = 42.0
FOOTER_LIMIT = 48.0

INK = (0.067, 0.118, 0.094)
MUTED = (0.310, 0.365, 0.337)
ACCENT = (0.255, 0.400, 0.326)
LINE = (0.820, 0.847, 0.831)
WHITE = (1.0, 1.0, 1.0)

_FALLBACK_CHARACTERS = {
    "\u00a0": " ",
    "\u2010": "-",
    "\u2011": "-",
    "\u2212": "-",
    "\u2026": "...",
    "\u2190": "<-",
    "\u2192": "->",
}


class PdfRenderError(ContentError):
    """Raised when profile content cannot be represented safely in the PDF."""


def _number(value: float) -> str:
    rendered = f"{value:.3f}".rstrip("0").rstrip(".")
    return rendered if rendered != "-0" else "0"


def _colour(value: tuple[float, float, float]) -> str:
    return " ".join(_number(channel) for channel in value)


def _winansi_text(value: str) -> str:
    """Return text representable by PDF's standard WinAnsi font encoding."""
    rendered: list[str] = []
    for character in value:
        try:
            character.encode("cp1252")
        except UnicodeEncodeError:
            replacement = _FALLBACK_CHARACTERS.get(character)
            if replacement is None:
                raise PdfRenderError(
                    "CV PDF cannot encode unsupported character "
                    f"U+{ord(character):04X} ({character!r})"
                )
            rendered.append(replacement)
        else:
            rendered.append(character)
    return "".join(rendered)


def _pdf_string(value: str) -> bytes:
    escaped = bytearray(b"(")
    for byte in _winansi_text(value).encode("cp1252"):
        if byte in b"\\()":
            escaped.extend(b"\\")
            escaped.append(byte)
        elif byte < 32 or byte > 126:
            escaped.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            escaped.append(byte)
    escaped.extend(b")")
    return bytes(escaped)


def _pdf_unicode_string(value: str) -> bytes:
    encoded = b"\xfe\xff" + value.encode("utf-16-be")
    return b"<" + encoded.hex().upper().encode("ascii") + b">"


def _pdf_uri(value: str) -> bytes:
    if not value.startswith("https://"):
        raise PdfRenderError(f"CV PDF link must use HTTPS: {value!r}")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as error:
        raise PdfRenderError(f"CV PDF link must be ASCII-safe: {value!r}") from error
    return _pdf_string(value)


def _width_table(groups: tuple[tuple[int, str], ...]) -> dict[str, int]:
    widths = {chr(code): 556 for code in range(32, 127)}
    assigned: set[str] = set()
    for width, characters in groups:
        for character in characters:
            if character in assigned:
                raise ValueError(f"duplicate Helvetica width for {character!r}")
            assigned.add(character)
            widths[character] = width
    return widths


_HELVETICA_WIDTHS = _width_table(
    (
        (191, "'"),
        (222, "ijl"),
        (260, "|"),
        (278, " !,./:;I[]\\ft"),
        (333, "()-`r"),
        (334, "{}"),
        (355, '"'),
        (389, "*"),
        (469, "^"),
        (500, "Jcksvxyz"),
        (584, "+<=>~"),
        (611, "FTZ"),
        (667, "ABEKPSVXY&"),
        (722, "CDHNRUw"),
        (778, "GOQ"),
        (833, "Mm"),
        (889, "%"),
        (944, "W"),
        (1015, "@"),
    )
)

_HELVETICA_BOLD_WIDTHS = _width_table(
    (
        (238, "'"),
        (278, " ,./I\\ijl"),
        (280, "|"),
        (333, "!():;-[]`ft"),
        (389, "*r{}"),
        (474, '"'),
        (500, "z"),
        (584, "+<=>^~"),
        (611, "FLTZ?bdghnopqu"),
        (667, "EPSVXY"),
        (722, "ABCDHKNRU&"),
        (778, "GOQw"),
        (833, "M"),
        (889, "%m"),
        (944, "W"),
        (975, "@"),
    )
)

_HELVETICA_PUNCTUATION_WIDTHS = {
    "•": 350,
    "·": 278,
    "–": 556,
    "—": 1000,
    "‘": 222,
    "’": 222,
    "“": 333,
    "”": 333,
}

_HELVETICA_BOLD_PUNCTUATION_WIDTHS = {
    **_HELVETICA_PUNCTUATION_WIDTHS,
    "‘": 278,
    "’": 278,
    "“": 500,
    "”": 500,
}


def _glyph_width(character: str, *, bold: bool) -> float:
    widths = _HELVETICA_BOLD_WIDTHS if bold else _HELVETICA_WIDTHS
    punctuation = (
        _HELVETICA_BOLD_PUNCTUATION_WIDTHS
        if bold
        else _HELVETICA_PUNCTUATION_WIDTHS
    )
    if character in punctuation:
        return punctuation[character] / 1000
    if character in widths:
        return widths[character] / 1000

    decomposed = unicodedata.normalize("NFKD", character)
    base = next((value for value in decomposed if value in widths), None)
    return widths.get(base or "?", 556) / 1000


def _text_width(value: str, size: float, *, bold: bool = False) -> float:
    return sum(
        _glyph_width(character, bold=bold) for character in _winansi_text(value)
    ) * size


def _split_long_word(word: str, width: float, size: float, *, bold: bool) -> list[str]:
    fragments: list[str] = []
    current = ""
    for character in word:
        candidate = current + character
        if current and _text_width(candidate, size, bold=bold) > width:
            fragments.append(current)
            current = character
        else:
            current = candidate
    if current:
        fragments.append(current)
    return fragments


def _wrap_text(value: str, width: float, size: float, *, bold: bool = False) -> list[str]:
    words: list[str] = []
    for word in _winansi_text(value).split():
        if _text_width(word, size, bold=bold) <= width:
            words.append(word)
        else:
            words.extend(_split_long_word(word, width, size, bold=bold))

    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(candidate, size, bold=bold) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


@dataclass(frozen=True)
class _Link:
    left: float
    bottom: float
    right: float
    top: float
    url: str
    label: str
    structure_mcid: int


@dataclass
class _Page:
    commands: list[bytes] = field(default_factory=list)
    links: list[_Link] = field(default_factory=list)
    structure_tags: list[str] = field(default_factory=list)

    def _text_command(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float,
        bold: bool,
        colour: tuple[float, float, float],
    ) -> bytes:
        font = "F2" if bold else "F1"
        return (
            f"BT /{font} {_number(size)} Tf {_colour(colour)} rg "
            f"1 0 0 1 {_number(x)} {_number(y)} Tm ".encode("ascii")
            + _pdf_string(value)
            + b" Tj ET"
        )

    def _marked(self, tag: str, commands: list[bytes]) -> int:
        mcid = len(self.structure_tags)
        self.structure_tags.append(tag)
        self.commands.append(f"/{tag} <</MCID {mcid}>> BDC".encode("ascii"))
        self.commands.extend(commands)
        self.commands.append(b"EMC")
        return mcid

    def _artifact(self, commands: list[bytes]) -> None:
        self.commands.append(b"/Artifact BMC")
        self.commands.extend(commands)
        self.commands.append(b"EMC")

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float,
        bold: bool = False,
        colour: tuple[float, float, float] = INK,
        tag: str = "P",
        url: str | None = None,
    ) -> float:
        command = self._text_command(
            x,
            y,
            value,
            size=size,
            bold=bold,
            colour=colour,
        )
        mcid = self._marked(tag, [command])
        width = _text_width(value, size, bold=bold)
        if url:
            self.links.append(
                _Link(
                    x,
                    y - 3.0,
                    x + width + 2.0,
                    y + size + 2.0,
                    url,
                    value,
                    mcid,
                )
            )
            self.line(x, y - 2.0, x + width, y - 2.0, colour=colour, width=0.45)
        return width

    def artifact_text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float,
        bold: bool = False,
        colour: tuple[float, float, float] = INK,
    ) -> float:
        self._artifact(
            [
                self._text_command(
                    x,
                    y,
                    value,
                    size=size,
                    bold=bold,
                    colour=colour,
                )
            ]
        )
        return _text_width(value, size, bold=bold)

    def wrapped_text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        width: float,
        size: float,
        leading: float,
        bold: bool = False,
        colour: tuple[float, float, float] = INK,
        tag: str = "P",
        url: str | None = None,
    ) -> float:
        lines = _wrap_text(value, width, size, bold=bold)
        commands: list[bytes] = []
        link_rectangles: list[tuple[float, float, float, float]] = []
        baseline = y
        for line in lines:
            commands.append(
                self._text_command(
                    x,
                    baseline,
                    line,
                    size=size,
                    bold=bold,
                    colour=colour,
                )
            )
            if url:
                line_width = _text_width(line, size, bold=bold)
                link_rectangles.append(
                    (
                        x,
                        baseline - 3.0,
                        x + line_width + 2.0,
                        baseline + size + 2.0,
                    )
                )
            baseline -= leading
        mcid = self._marked(tag, commands)
        for line, rectangle in zip(lines, link_rectangles, strict=False):
            left, bottom, right, top = rectangle
            self.links.append(
                _Link(left, bottom, right, top, url or "", value, mcid)
            )
            line_width = _text_width(line, size, bold=bold)
            self.line(
                x,
                bottom + 1.0,
                x + line_width,
                bottom + 1.0,
                colour=colour,
                width=0.4,
            )
        return baseline

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        colour: tuple[float, float, float] = LINE,
        width: float = 0.6,
    ) -> None:
        self._artifact(
            [
                (
                    f"q {_number(width)} w {_colour(colour)} RG "
                    f"{_number(x1)} {_number(y1)} m "
                    f"{_number(x2)} {_number(y2)} l S Q"
                ).encode("ascii")
            ]
        )

    def rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        colour: tuple[float, float, float],
    ) -> None:
        self._artifact(
            [
                (
                    f"q {_colour(colour)} rg {_number(x)} {_number(y)} "
                    f"{_number(width)} {_number(height)} re f Q"
                ).encode("ascii")
            ]
        )


def _section_heading(page: _Page, x: float, y: float, title: str, width: float) -> float:
    page.text(x, y, title.upper(), size=8.0, bold=True, colour=ACCENT, tag="H2")
    page.line(x, y - 5.0, x + width, y - 5.0, colour=LINE, width=0.65)
    return y - 20.0


def _contact_links(page: _Page, profile: Profile, y: float) -> None:
    size = 6.8
    separator = "  ·  "
    total_width = sum(
        _text_width(social.label, size, bold=True) for social in profile.socials
    ) + (_text_width(separator, size) * (len(profile.socials) - 1))
    x = A4_WIDTH - MARGIN - total_width
    if x < A4_WIDTH / 2:
        raise PdfRenderError("CV PDF contact links do not fit in the header")

    for index, social in enumerate(profile.socials):
        x += page.text(
            x,
            y,
            social.label,
            size=size,
            bold=True,
            colour=ACCENT,
            tag="Link",
            url=social.url,
        )
        if index < len(profile.socials) - 1:
            x += page.artifact_text(
                x,
                y,
                separator,
                size=size,
                colour=MUTED,
            )


def _document_header(page: _Page, profile: Profile, *, continued: bool) -> float:
    page.rectangle(0.0, 0.0, A4_WIDTH, A4_HEIGHT, colour=WHITE)
    page.rectangle(0.0, A4_HEIGHT - 7.0, A4_WIDTH, 7.0, colour=ACCENT)
    name_size = 20.0 if continued else 25.0
    name_y = 796.0 if continued else 793.0
    website = profile.site.canonical_url.removeprefix("https://").rstrip("/")
    website_width = _text_width(website, 8.0, bold=True)
    if continued:
        page.artifact_text(
            MARGIN,
            name_y,
            profile.site.name,
            size=name_size,
            bold=True,
        )
        page.artifact_text(
            MARGIN,
            name_y - 20.0,
            profile.site.role,
            size=9.4,
            bold=True,
            colour=ACCENT,
        )
        page.artifact_text(
            MARGIN,
            name_y - 35.0,
            profile.site.location,
            size=7.5,
            colour=MUTED,
        )
        page.artifact_text(
            A4_WIDTH - MARGIN - website_width,
            name_y - 1.0,
            website,
            size=8.0,
            bold=True,
            colour=ACCENT,
        )
        page.artifact_text(
            A4_WIDTH - MARGIN - _text_width("Curriculum vitae", 7.0),
            name_y - 19.0,
            "Curriculum vitae",
            size=7.0,
            colour=MUTED,
        )
    else:
        page.text(
            MARGIN,
            name_y,
            profile.site.name,
            size=name_size,
            bold=True,
            tag="H1",
        )
        page.text(
            MARGIN,
            name_y - 20.0,
            profile.site.role,
            size=9.4,
            bold=True,
            colour=ACCENT,
            tag="P",
        )
        page.text(
            MARGIN,
            name_y - 35.0,
            profile.site.location,
            size=7.5,
            colour=MUTED,
            tag="P",
        )
        page.text(
            A4_WIDTH - MARGIN - website_width,
            name_y - 1.0,
            website,
            size=8.0,
            bold=True,
            colour=ACCENT,
            tag="Link",
            url=f"{profile.site.canonical_url}/cv/",
        )
        page.text(
            A4_WIDTH - MARGIN - _text_width("Curriculum vitae", 7.0),
            name_y - 19.0,
            "Curriculum vitae",
            size=7.0,
            colour=MUTED,
            tag="P",
        )
        _contact_links(page, profile, name_y - 35.0)
    page.line(MARGIN, 746.0, A4_WIDTH - MARGIN, 746.0, colour=INK, width=1.1)
    return 727.0


def _footer(page: _Page, profile: Profile, number: int, total: int) -> None:
    page.line(MARGIN, 32.0, A4_WIDTH - MARGIN, 32.0, colour=LINE, width=0.5)
    footer = (
        f"{profile.site.canonical_url.removeprefix('https://')}  ·  "
        f"Updated {profile.site.last_updated}"
    )
    command = page._text_command(
        MARGIN,
        20.0,
        footer,
        size=6.3,
        bold=False,
        colour=MUTED,
    )
    page._artifact([command])
    page_number = f"{number} / {total}"
    number_width = _text_width(page_number, 6.3, bold=True)
    command = page._text_command(
        A4_WIDTH - MARGIN - number_width,
        20.0,
        page_number,
        size=6.3,
        bold=True,
        colour=MUTED,
    )
    page._artifact([command])


def _career_entry(
    page: _Page,
    x: float,
    y: float,
    width: float,
    entry: CareerEntry,
) -> float:
    y = page.wrapped_text(
        x,
        y,
        entry.role,
        width=width,
        size=9.4,
        leading=11.3,
        bold=True,
        tag="H3",
    )
    y -= 1.0
    y = page.wrapped_text(
        x,
        y,
        f"{entry.company}  ·  {entry.period}",
        width=width,
        size=7.6,
        leading=9.2,
        bold=True,
        colour=ACCENT,
        tag="P",
    )
    y -= 3.0
    y = page.wrapped_text(
        x,
        y,
        entry.summary,
        width=width,
        size=7.9,
        leading=10.2,
        colour=MUTED,
        tag="P",
    )
    y -= 6.0
    page.line(x, y + 2.0, x + width, y + 2.0, colour=LINE, width=0.4)
    return y - 4.0


def _education_entry(
    page: _Page,
    x: float,
    y: float,
    width: float,
    entry: Education,
) -> float:
    y = page.wrapped_text(
        x,
        y,
        entry.qualification,
        width=width,
        size=8.0,
        leading=9.8,
        bold=True,
        tag="H3",
    )
    y -= 1.0
    y = page.wrapped_text(
        x,
        y,
        f"{entry.institution}  ·  {entry.period}",
        width=width,
        size=7.0,
        leading=8.6,
        bold=True,
        colour=ACCENT,
        tag="P",
    )
    y -= 2.0
    y = page.wrapped_text(
        x,
        y,
        entry.summary,
        width=width,
        size=7.2,
        leading=9.2,
        colour=MUTED,
        tag="P",
    )
    return y - 8.0


def _expertise_entry(
    page: _Page,
    x: float,
    y: float,
    width: float,
    item: Expertise,
) -> float:
    y = page.wrapped_text(
        x,
        y,
        item.title,
        width=width,
        size=9.5,
        leading=11.2,
        bold=True,
        tag="H3",
    )
    y -= 2.0
    y = page.wrapped_text(
        x,
        y,
        item.summary,
        width=width,
        size=8.0,
        leading=10.2,
        colour=MUTED,
        tag="P",
    )
    y -= 2.0
    for detail in item.items:
        y = page.wrapped_text(
            x + 8.0,
            y,
            f"• {detail}",
            width=width - 8.0,
            size=7.7,
            leading=9.4,
            colour=INK,
            tag="P",
        )
    y -= 8.0
    page.line(x, y + 2.0, x + width, y + 2.0, colour=LINE, width=0.4)
    return y - 4.0


def _sidebar_item(
    page: _Page,
    x: float,
    y: float,
    width: float,
    title: str,
    detail: str,
    *,
    url: str | None = None,
) -> float:
    y = page.wrapped_text(
        x,
        y,
        title,
        width=width,
        size=8.0,
        leading=9.7,
        bold=True,
        colour=ACCENT if url else INK,
        tag="Link" if url else "H3",
        url=url,
    )
    y -= 1.0
    y = page.wrapped_text(
        x,
        y,
        detail,
        width=width,
        size=7.0,
        leading=8.8,
        colour=MUTED,
        tag="P",
    )
    return y - 10.0


def _ensure_page_fit(y: float, section: str) -> None:
    if y < FOOTER_LIMIT:
        raise PdfRenderError(f"CV PDF content exceeds the page in {section}: y={y:.1f}")


def _render_pages(profile: Profile) -> list[_Page]:
    page_one = _Page()
    y = _document_header(page_one, profile, continued=False)
    y = _section_heading(page_one, MARGIN, y, "Profile", A4_WIDTH - (2 * MARGIN))
    for paragraph in profile.site.cv_profile:
        y = page_one.wrapped_text(
            MARGIN,
            y,
            paragraph,
            width=A4_WIDTH - (2 * MARGIN),
            size=8.6,
            leading=11.3,
            colour=MUTED,
            tag="P",
        )
        y -= 5.0

    column_top = y - 2.0
    column_gap = 22.0
    sidebar_width = 157.0
    primary_width = A4_WIDTH - (2 * MARGIN) - column_gap - sidebar_width
    sidebar_x = MARGIN + primary_width + column_gap

    primary_y = _section_heading(page_one, MARGIN, column_top, "Experience", primary_width)
    for entry in profile.career:
        primary_y = _career_entry(page_one, MARGIN, primary_y, primary_width, entry)
    _ensure_page_fit(primary_y, "experience")

    sidebar_y = _section_heading(
        page_one,
        sidebar_x,
        column_top,
        "Education",
        sidebar_width,
    )
    for entry in profile.education:
        sidebar_y = _education_entry(
            page_one,
            sidebar_x,
            sidebar_y,
            sidebar_width,
            entry,
        )

    sidebar_y = _section_heading(
        page_one,
        sidebar_x,
        sidebar_y - 1.0,
        "Credentials earned",
        sidebar_width,
    )
    for certification in profile.certifications:
        sidebar_y = page_one.wrapped_text(
            sidebar_x,
            sidebar_y,
            certification.name,
            width=sidebar_width,
            size=7.2,
            leading=8.7,
            bold=True,
            tag="P",
        )
        sidebar_y = page_one.wrapped_text(
            sidebar_x,
            sidebar_y - 0.5,
            certification.issuer,
            width=sidebar_width,
            size=6.6,
            leading=7.8,
            colour=MUTED,
            tag="P",
        )
        sidebar_y -= 4.5
    _ensure_page_fit(sidebar_y, "credentials")
    _footer(page_one, profile, 1, 2)

    page_two = _Page()
    page_two_top = _document_header(page_two, profile, continued=True)
    primary_y = _section_heading(
        page_two,
        MARGIN,
        page_two_top,
        "Technical expertise",
        primary_width,
    )
    for item in profile.expertise:
        primary_y = _expertise_entry(page_two, MARGIN, primary_y, primary_width, item)
    _ensure_page_fit(primary_y, "technical expertise")

    sidebar_y = _section_heading(
        page_two,
        sidebar_x,
        page_two_top,
        "Open-source organisation",
        sidebar_width,
    )
    for organisation in profile.open_source_organisations:
        sidebar_y = page_two.wrapped_text(
            sidebar_x,
            sidebar_y,
            organisation.name,
            width=sidebar_width,
            size=8.4,
            leading=10.0,
            bold=True,
            colour=ACCENT,
            tag="Link",
            url=organisation.website_url,
        )
        sidebar_y = page_two.wrapped_text(
            sidebar_x,
            sidebar_y - 3.0,
            organisation.summary,
            width=sidebar_width,
            size=7.5,
            leading=9.5,
            colour=MUTED,
            tag="P",
        )
        sidebar_y -= 12.0

    sidebar_y = _section_heading(
        page_two,
        sidebar_x,
        sidebar_y,
        "Selected open source",
        sidebar_width,
    )
    for project in profile.projects[:4]:
        sidebar_y = _sidebar_item(
            page_two,
            sidebar_x,
            sidebar_y,
            sidebar_width,
            project.name,
            project.repository,
            url=project.url,
        )

    sidebar_y = _section_heading(
        page_two,
        sidebar_x,
        sidebar_y,
        "Community & recognition",
        sidebar_width,
    )
    for item in profile.recognition:
        sidebar_y = _sidebar_item(
            page_two,
            sidebar_x,
            sidebar_y,
            sidebar_width,
            item.title,
            item.detail,
            url=item.url,
        )
    _ensure_page_fit(sidebar_y, "community and recognition")
    _footer(page_two, profile, 2, 2)

    return [page_one, page_two]


class _Objects:
    def __init__(self) -> None:
        self.values: list[bytes | None] = [None]

    def reserve(self) -> int:
        self.values.append(None)
        return len(self.values) - 1

    def add(self, value: bytes) -> int:
        identifier = self.reserve()
        self.set(identifier, value)
        return identifier

    def set(self, identifier: int, value: bytes) -> None:
        if self.values[identifier] is not None:
            raise ValueError(f"PDF object {identifier} was already assigned")
        self.values[identifier] = value


def _stream(payload: bytes) -> bytes:
    return (
        f"<< /Length {len(payload)} >>\nstream\n".encode("ascii")
        + payload
        + b"\nendstream"
    )


def _to_unicode_cmap() -> bytes:
    mappings: list[tuple[int, str]] = []
    for byte in range(256):
        try:
            character = bytes([byte]).decode("cp1252")
        except UnicodeDecodeError:
            continue
        mappings.append((byte, character.encode("utf-16-be").hex().upper()))

    lines = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /WinAnsiUTF16 def",
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<00> <FF>",
        "endcodespacerange",
    ]
    for start in range(0, len(mappings), 100):
        group = mappings[start : start + 100]
        lines.append(f"{len(group)} beginbfchar")
        lines.extend(f"<{byte:02X}> <{unicode_value}>" for byte, unicode_value in group)
        lines.append("endbfchar")
    lines.extend(
        [
            "endcmap",
            "CMapName currentdict /CMap defineresource pop",
            "end",
            "end",
        ]
    )
    return "\n".join(lines).encode("ascii")


def _assemble_pdf(profile: Profile, pages: list[_Page]) -> bytes:
    objects = _Objects()
    catalog_id = objects.reserve()
    pages_id = objects.reserve()
    cmap_id = objects.add(_stream(_to_unicode_cmap()))
    regular_font_id = objects.add(
        (
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            f"/Encoding /WinAnsiEncoding /ToUnicode {cmap_id} 0 R >>"
        ).encode("ascii")
    )
    bold_font_id = objects.add(
        (
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            f"/Encoding /WinAnsiEncoding /ToUnicode {cmap_id} 0 R >>"
        ).encode("ascii")
    )
    info_id = objects.reserve()
    structure_root_id = objects.reserve()
    document_structure_id = objects.reserve()
    parent_tree_id = objects.reserve()

    page_records: list[tuple[_Page, int, int]] = []
    for page in pages:
        page_id = objects.reserve()
        content = b"\n".join(page.commands) + b"\n"
        content_id = objects.add(_stream(content))
        page_records.append((page, page_id, content_id))

    all_structure_ids: list[int] = []
    page_structure_ids: list[list[int]] = []
    for page, _, _ in page_records:
        structure_ids = [objects.reserve() for _ in page.structure_tags]
        page_structure_ids.append(structure_ids)
        all_structure_ids.extend(structure_ids)

    next_parent_key = len(pages)
    page_annotations: list[list[tuple[_Link, int, int]]] = []
    for page, page_id, _ in page_records:
        annotation_records: list[tuple[_Link, int, int]] = []
        for link in page.links:
            if not (
                0 <= link.left < link.right <= A4_WIDTH
                and 0 <= link.bottom < link.top <= A4_HEIGHT
            ):
                raise PdfRenderError(f"CV PDF link is outside the page: {link!r}")
            parent_key = next_parent_key
            next_parent_key += 1
            annotation_id = objects.add(
                (
                    "<< /Type /Annot /Subtype /Link /F 4 /H /I "
                    f"/P {page_id} 0 R /StructParent {parent_key} "
                    f"/Rect [{_number(link.left)} {_number(link.bottom)} "
                    f"{_number(link.right)} {_number(link.top)}] "
                    "/Border [0 0 0] /Contents "
                ).encode("ascii")
                + _pdf_unicode_string(link.label)
                + b" /A << /S /URI /URI "
                + _pdf_uri(link.url)
                + b" >> >>"
            )
            annotation_records.append((link, annotation_id, parent_key))
        page_annotations.append(annotation_records)

    for page_index, (page, page_id, _) in enumerate(page_records):
        structure_ids = page_structure_ids[page_index]
        annotation_records = page_annotations[page_index]
        for mcid, (tag, structure_id) in enumerate(
            zip(page.structure_tags, structure_ids, strict=True)
        ):
            marked_content = (
                f"<< /Type /MCR /Pg {page_id} 0 R /MCID {mcid} >>"
            )
            if tag == "Link":
                object_references = " ".join(
                    f"<< /Type /OBJR /Pg {page_id} 0 R /Obj {annotation_id} 0 R >>"
                    for link, annotation_id, _ in annotation_records
                    if link.structure_mcid == mcid
                )
                kids = f"[{marked_content} {object_references}]"
            else:
                kids = marked_content
            objects.set(
                structure_id,
                (
                    f"<< /Type /StructElem /S /{tag} "
                    f"/P {document_structure_id} 0 R /Pg {page_id} 0 R /K {kids} >>"
                ).encode("ascii")
            )

    for page_index, (_, page_id, content_id) in enumerate(page_records):
        annotation_ids = [
            annotation_id
            for _, annotation_id, _ in page_annotations[page_index]
        ]
        annotations = ""
        if annotation_ids:
            references = " ".join(f"{identifier} 0 R" for identifier in annotation_ids)
            annotations = f" /Annots [{references}]"
        objects.set(
            page_id,
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {_number(A4_WIDTH)} {_number(A4_HEIGHT)}] "
                f"/StructParents {page_index} /Tabs /S "
                "/Resources << /Font << "
                f"/F1 {regular_font_id} 0 R /F2 {bold_font_id} 0 R"
                " >> >> "
                f"/Contents {content_id} 0 R{annotations} >>"
            ).encode("ascii"),
        )

    page_references = " ".join(
        f"{page_id} 0 R" for _, page_id, _ in page_records
    )
    objects.set(
        pages_id,
        (
            f"<< /Type /Pages /Kids [{page_references}] /Count {len(pages)} >>"
        ).encode("ascii"),
    )

    structure_references = " ".join(
        f"{identifier} 0 R" for identifier in all_structure_ids
    )
    objects.set(
        structure_root_id,
        (
            f"<< /Type /StructTreeRoot /K [{document_structure_id} 0 R] "
            f"/ParentTree {parent_tree_id} 0 R "
            f"/ParentTreeNextKey {next_parent_key} >>"
        ).encode("ascii"),
    )
    objects.set(
        document_structure_id,
        (
            f"<< /Type /StructElem /S /Document /P {structure_root_id} 0 R "
            f"/K [{structure_references}] >>"
        ).encode("ascii"),
    )
    page_parent_numbers = [
        f"{page_index} [{ ' '.join(f'{identifier} 0 R' for identifier in identifiers) }]"
        for page_index, identifiers in enumerate(page_structure_ids)
    ]
    annotation_parent_numbers = [
        f"{parent_key} {page_structure_ids[page_index][link.structure_mcid]} 0 R"
        for page_index, annotation_records in enumerate(page_annotations)
        for link, _, parent_key in annotation_records
    ]
    parent_numbers = " ".join(page_parent_numbers + annotation_parent_numbers)
    objects.set(
        parent_tree_id,
        f"<< /Nums [{parent_numbers}] >>".encode("ascii"),
    )

    objects.set(
        catalog_id,
        (
            f"<< /Type /Catalog /Pages {pages_id} 0 R "
            f"/StructTreeRoot {structure_root_id} 0 R "
            "/MarkInfo << /Marked true >> /Lang (en-GB) "
            "/ViewerPreferences << /DisplayDocTitle true >> /PageLayout /OneColumn >>"
        ).encode("ascii"),
    )
    objects.set(
        info_id,
        b"<< /Title "
        + _pdf_unicode_string(f"{profile.site.name} CV — {profile.site.short_role}")
        + b" /Author "
        + _pdf_unicode_string(profile.site.name)
        + b" /Subject "
        + _pdf_unicode_string("Professional curriculum vitae")
        + b" /Creator "
        + _pdf_unicode_string("marcincuber.github.io static-site generator")
        + b" /Producer "
        + _pdf_unicode_string("Python standard-library PDF renderer")
        + b" >>",
    )

    if any(value is None for value in objects.values[1:]):
        raise ValueError("PDF contains an unassigned object")

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for identifier, value in enumerate(objects.values[1:], start=1):
        offsets.append(len(document))
        document.extend(f"{identifier} 0 obj\n".encode("ascii"))
        document.extend(value or b"")
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects.values)}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects.values)} /Root {catalog_id} 0 R "
            f"/Info {info_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def render_cv_pdf(profile: Profile) -> bytes:
    """Render *profile* as a deterministic, selectable-text A4 PDF."""
    return _assemble_pdf(profile, _render_pages(profile))
