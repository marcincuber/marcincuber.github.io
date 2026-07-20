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


def _fingerprinted_copy(source: Path, destination: Path) -> str:
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()[:12]
    filename = f"{source.stem}.{digest}{source.suffix}"
    target = destination / "assets" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return f"assets/{filename}"


def _static_copy(source: Path, destination: Path) -> str:
    target = destination / "assets" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return f"assets/{source.name}"


def _page(
    template: Template,
    profile: Profile,
    *,
    title: str,
    description: str,
    canonical_url: str,
    body: str,
    body_class: str,
    asset_prefix: str,
    assets: dict[str, str],
) -> str:
    from html import escape

    return template.substitute(
        page_title=escape(title),
        description=escape(description, quote=True),
        canonical_url=escape(canonical_url, quote=True),
        social_image=escape(
            f"{profile.site.canonical_url}/assets/social-card.svg", quote=True
        ),
        structured_data=structured_data(profile, canonical_url),
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
            "icon": _static_copy(static_root / "favicon.svg", staging),
        }
        _static_copy(static_root / "social-card.svg", staging)

        home_url = f"{profile.site.canonical_url}/"
        home = _page(
            base_template,
            profile,
            title=f"{profile.site.name} — {profile.site.role}",
            description=profile.site.description,
            canonical_url=home_url,
            body=render_home(profile),
            body_class="home-page",
            asset_prefix="",
            assets=assets,
        )
        _write(staging / "index.html", home)

        cv_url = f"{profile.site.canonical_url}/cv/"
        cv = _page(
            base_template,
            profile,
            title=f"CV — {profile.site.name}",
            description=(
                f"Professional CV for {profile.site.name}, {profile.site.role}, "
                "covering experience, expertise, education and certifications."
            ),
            canonical_url=cv_url,
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
            title=f"Page not found — {profile.site.name}",
            description="The requested page could not be found.",
            canonical_url=not_found_url,
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
            f"  <url><loc>{home_url}</loc><priority>1.0</priority></url>\n"
            f"  <url><loc>{cv_url}</loc><priority>0.8</priority></url>\n"
            "</urlset>",
        )
        manifest = {
            "name": f"{profile.site.name} — Cloud Engineering",
            "short_name": profile.site.name,
            "start_url": "/",
            "display": "minimal-ui",
            "background_color": "#07110f",
            "theme_color": "#07110f",
            "icons": [
                {
                    "src": "/assets/favicon.svg",
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
