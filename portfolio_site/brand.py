"""Single-source CUBE/R identity geometry and generated SVG assets."""

from __future__ import annotations

from html import escape


BRAND_TITLE = "Cuber cube-R identity mark"
BRAND_DESCRIPTION = (
    "An isometric cube followed by a registered-style R roundel."
)

BRAND_ELEMENTS = (
    '<rect x="1" y="1" width="62" height="62" rx="15" fill="#07110f" '
    'stroke="#d8f6e8" stroke-opacity=".16" stroke-width="2"/>',
    '<path d="m27.5 10 17.5 9.8-17.5 9.8L10 19.8 27.5 10Z" '
    'fill="#b9f36a"/>',
    '<path d="m10 19.8 17.5 9.8v20.2L10 40V19.8Z" fill="#6fe1d2"/>',
    '<path d="m27.5 29.6 17.5-9.8V40l-17.5 9.8V29.6Z" '
    'fill="#2f957d"/>',
    '<path d="m27.5 10 17.5 9.8v20.3l-17.5 9.7L10 40V19.8L27.5 10Z'
    'm0 19.6L10 19.8m17.5 9.8L45 19.8m-17.5 9.8v20.2" '
    'fill="none" stroke="#07110f" stroke-linecap="round" '
    'stroke-linejoin="round" stroke-width="2.2"/>',
    '<circle cx="49.5" cy="14.5" r="9.5" fill="#07110f" '
    'stroke="#b9f36a" stroke-width="2"/>',
    '<path d="M45.25 20.5v-11h4.5c2.6 0 4.2 1.35 4.2 3.55 0 1.55-.82 '
    '2.75-2.25 3.28l2.7 4.17h-3.1L49 16.9h-1v3.6h-2.75ZM48 '
    '14.65h1.5c1.1 0 1.68-.46 1.68-1.32 0-.85-.58-1.3-1.68-1.3H48'
    'v2.62Z" fill="#b9f36a"/>',
)


def _indented_elements(indent: str) -> str:
    return "\n".join(f"{indent}{element}" for element in BRAND_ELEMENTS)


def brand_mark(extra_class: str = "") -> str:
    """Return the decorative inline identity mark used in page lockups."""
    classes = "brand-mark"
    if extra_class:
        classes = f"{classes} {extra_class}"
    return (
        f'<svg class="{escape(classes, quote=True)}" viewBox="0 0 64 64" '
        'aria-hidden="true" focusable="false">'
        f'{"".join(BRAND_ELEMENTS)}</svg>'
    )


def favicon_svg() -> str:
    """Return the standalone, accessible SVG favicon."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
        'role="img" aria-labelledby="cuber-logo-title cuber-logo-desc">\n'
        f'  <title id="cuber-logo-title">{BRAND_TITLE}</title>\n'
        f'  <desc id="cuber-logo-desc">{BRAND_DESCRIPTION}</desc>\n'
        f"{_indented_elements('  ')}\n"
        "</svg>"
    )


def social_card_svg(
    *,
    name: str,
    role: str,
    short_role: str,
    description: str,
    focus_line: str,
    location: str,
    canonical_url: str,
) -> str:
    """Return the 1200×630 Open Graph card with the shared CUBE/R mark."""
    role_primary, separator, role_secondary = role.partition(" & ")
    second_role_line = (
        f"&amp; {escape(role_secondary)}" if separator else ""
    )
    display_url = canonical_url.removeprefix("https://").rstrip("/")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" '
        'viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{escape(name)} — {escape(short_role)}</title>\n'
        f'  <desc id="desc">{escape(description)}</desc>\n'
        "  <defs>\n"
        '    <radialGradient id="glow" cx="80%" cy="10%" r="80%">\n'
        '      <stop offset="0" stop-color="#214c3d"/>\n'
        '      <stop offset="1" stop-color="#07110f"/>\n'
        "    </radialGradient>\n"
        '    <pattern id="grid" width="64" height="55.426" '
        'patternUnits="userSpaceOnUse">\n'
        '      <path d="M0 0 32 18.475 64 0M0 36.95l32 18.476L64 36.95'
        'M32 18.475v36.951" fill="none" stroke="#d8f6e8" '
        'stroke-opacity=".05"/>\n'
        "    </pattern>\n"
        "  </defs>\n"
        '  <rect width="1200" height="630" fill="url(#glow)"/>\n'
        '  <rect width="1200" height="630" fill="url(#grid)"/>\n'
        '  <g transform="translate(84 78)">\n'
        '    <g transform="scale(.90625)" aria-hidden="true">\n'
        f"{_indented_elements('      ')}\n"
        "    </g>\n"
        '    <text x="78" y="25" font-family="ui-sans-serif, sans-serif" '
        f'font-size="20" font-weight="700" fill="#f8fff9">{escape(name)}</text>\n'
        '    <text x="78" y="49" font-family="ui-monospace, monospace" '
        'font-size="12" letter-spacing="1.5" fill="#9eaaa5">'
        f"{escape(short_role.upper())}</text>\n"
        "  </g>\n"
        '  <g transform="translate(84 220)">\n'
        '    <text font-family="ui-monospace, monospace" font-size="16" '
        'font-weight="700" fill="#6fe1d2">$ whoami</text>\n'
        '    <text y="75" font-family="ui-sans-serif, sans-serif" '
        'font-size="55" font-weight="700" letter-spacing="-2.8" '
        f'fill="#f8fff9">{escape(role_primary)}</text>\n'
        '    <text y="145" font-family="ui-sans-serif, sans-serif" '
        'font-size="48" font-weight="700" letter-spacing="-2.4" '
        f'fill="#f8fff9">{second_role_line}</text>\n'
        '    <text y="208" font-family="ui-sans-serif, sans-serif" '
        f'font-size="22" fill="#aab7b1">{escape(focus_line)}</text>\n'
        "  </g>\n"
        '  <g transform="translate(84 566)">\n'
        '    <circle cx="6" cy="-6" r="6" fill="#b9f36a"/>\n'
        '    <text x="24" font-family="ui-monospace, monospace" font-size="15" '
        f'fill="#d8e2dd">{escape(display_url)}</text>\n'
        '    <text x="1032" text-anchor="end" '
        'font-family="ui-monospace, monospace" font-size="15" '
        f'fill="#9eaaa5">{escape(location)}</text>\n'
        "  </g>\n"
        "</svg>"
    )
