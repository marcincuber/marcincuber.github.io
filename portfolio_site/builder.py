"""Deterministic static build with asset fingerprinting and atomic output."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
from string import Template
import tempfile

from .brand import BRAND_VOID, favicon_svg, social_card_svg
from .content import ContentError, Profile
from .render import render_cv, render_home, render_not_found, structured_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BuildResult:
    output: Path
    files: tuple[Path, ...]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _fingerprinted_asset(
    filename: str,
    payload: bytes,
    destination: Path,
) -> str:
    digest = hashlib.sha256(payload).hexdigest()[:12]
    source_name = Path(filename)
    output_name = f"{source_name.stem}.{digest}{source_name.suffix}"
    target = destination / "assets" / output_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return f"assets/{output_name}"


def _fingerprinted_copy(source: Path, destination: Path) -> str:
    return _fingerprinted_asset(source.name, source.read_bytes(), destination)


def _svg_payload(content: str) -> bytes:
    return (content.rstrip() + "\n").encode("utf-8")


def _page(
    template: Template,
    profile: Profile,
    *,
    page_kind: str,
    title: str,
    description: str,
    canonical_url: str,
    robots: str,
    og_type: str,
    body: str,
    body_class: str,
    asset_prefix: str,
    assets: dict[str, str],
) -> str:
    from html import escape

    first_name, _, last_name = profile.site.name.partition(" ")
    identity_links = "\n".join(
        f'    <link rel="me" href="{escape(social.url, quote=True)}">'
        for social in profile.socials
    )
    profile_metadata = ""
    if og_type == "profile":
        profile_metadata = (
            f'    <meta property="profile:first_name" '
            f'content="{escape(first_name, quote=True)}">\n'
            f'    <meta property="profile:last_name" '
            f'content="{escape(last_name, quote=True)}">'
        )
    social_image_alt = f"{title} — social preview"
    return template.substitute(
        page_title=escape(title),
        description=escape(description, quote=True),
        robots=escape(robots, quote=True),
        theme_color=BRAND_VOID,
        canonical_url=escape(canonical_url, quote=True),
        identity_links=identity_links,
        og_type=escape(og_type, quote=True),
        site_name=escape(profile.site.name, quote=True),
        social_image=escape(
            f"{profile.site.canonical_url}/{assets['social']}", quote=True
        ),
        social_image_alt=escape(social_image_alt, quote=True),
        profile_metadata=profile_metadata,
        structured_data=structured_data(
            profile,
            canonical_url,
            f"{profile.site.canonical_url}/{assets['avatar']}",
            page_name=title,
            page_description=description,
            page_kind=page_kind,
        ),
        asset_prefix=asset_prefix,
        css_asset=assets["css"],
        js_asset=assets["js"],
        icon_asset=assets["icon"],
        body_class=body_class,
        body=body,
    )


def _assert_safe_output(output: Path) -> Path:
    resolved = output.expanduser().resolve()
    forbidden = {
        Path(resolved.anchor),
        Path.home().resolve(),
        PROJECT_ROOT.resolve(),
        PROJECT_ROOT.parent.resolve(),
    }
    if resolved in forbidden:
        raise ContentError(f"refusing to use unsafe build output: {resolved}")
    return resolved


def build_site(
    output: Path,
    *,
    content_path: Path | None = None,
    project_root: Path = PROJECT_ROOT,
) -> BuildResult:
    """Build the complete site into *output* and return its materialised files."""
    output = _assert_safe_output(output)
    content_path = content_path or project_root / "content" / "profile.json"
    profile = Profile.load(content_path)
    base_template = Template(
        (project_root / "templates" / "base.html").read_text(encoding="utf-8")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=".portfolio-build-", dir=str(output.parent))
    )

    try:
        static_root = project_root / "static"
        assets = {
            "css": _fingerprinted_copy(static_root / "styles.css", staging),
            "js": _fingerprinted_copy(static_root / "site.js", staging),
            "icon": _fingerprinted_asset(
                "favicon.svg",
                _svg_payload(favicon_svg()),
                staging,
            ),
            "social": _fingerprinted_asset(
                "social-card.svg",
                _svg_payload(
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
                ),
                staging,
            ),
            "avatar": _fingerprinted_copy(
                static_root / profile.site.avatar_asset,
                staging,
            ),
            "github_avatar": _fingerprinted_copy(
                static_root / profile.site.github_avatar_asset,
                staging,
            ),
        }

        home_url = f"{profile.site.canonical_url}/"
        home = _page(
            base_template,
            profile,
            page_kind="home",
            title=f"{profile.site.name} — {profile.site.role}",
            description=profile.site.description,
            canonical_url=home_url,
            robots=(
                "index, follow, max-image-preview:large, "
                "max-snippet:-1, max-video-preview:-1"
            ),
            og_type="profile",
            body=render_home(
                profile,
                avatar_asset=assets["avatar"],
                github_avatar_asset=assets["github_avatar"],
            ),
            body_class="home-page",
            asset_prefix="",
            assets=assets,
        )
        _write(staging / "index.html", home)

        cv_url = f"{profile.site.canonical_url}/cv/"
        cv = _page(
            base_template,
            profile,
            page_kind="cv",
            title=f"{profile.site.name} CV — {profile.site.short_role}",
            description=(
                f"{profile.site.name}'s professional CV: principal-level AWS, "
                "Kubernetes, Terraform, GitOps and platform engineering experience, "
                "plus education and certifications."
            ),
            canonical_url=cv_url,
            robots=(
                "index, follow, max-image-preview:large, "
                "max-snippet:-1, max-video-preview:-1"
            ),
            og_type="profile",
            body=render_cv(profile),
            body_class="cv-document",
            asset_prefix="../",
            assets=assets,
        )
        _write(staging / "cv" / "index.html", cv)

        not_found_url = f"{profile.site.canonical_url}/404.html"
        not_found = _page(
            base_template,
            profile,
            page_kind="not_found",
            title=f"Page not found — {profile.site.name}",
            description="The requested page could not be found.",
            canonical_url=not_found_url,
            robots="noindex, follow",
            og_type="website",
            body=render_not_found(profile),
            body_class="not-found-page",
            asset_prefix="",
            assets=assets,
        )
        _write(staging / "404.html", not_found)

        _write(
            staging / "robots.txt",
            f"User-agent: *\nAllow: /\n\nSitemap: {profile.site.canonical_url}/sitemap.xml",
        )
        _write(
            staging / "sitemap.xml",
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{home_url}</loc>"
            f"<lastmod>{profile.site.last_updated}</lastmod></url>\n"
            f"  <url><loc>{cv_url}</loc>"
            f"<lastmod>{profile.site.last_updated}</lastmod></url>\n"
            "</urlset>",
        )
        manifest = {
            "id": "/",
            "name": f"{profile.site.name} — Cloud Engineering",
            "short_name": profile.site.name,
            "description": profile.site.description,
            "lang": "en-GB",
            "start_url": "/",
            "scope": "/",
            "display": "minimal-ui",
            "background_color": BRAND_VOID,
            "theme_color": BRAND_VOID,
            "icons": [
                {
                    "src": f"/{assets['icon']}",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any",
                }
            ],
        }
        _write(
            staging / "site.webmanifest",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        _write(staging / ".nojekyll", "")

        if output.exists():
            if output.is_symlink():
                raise ContentError(f"refusing to replace symlinked output: {output}")
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    files = tuple(path for path in sorted(output.rglob("*")) if path.is_file())
    return BuildResult(output=output, files=files)
