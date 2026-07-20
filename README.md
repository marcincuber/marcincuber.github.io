# Marcin Cuber — professional cloud engineering profile

A fast, dependency-free portfolio generated with Python and deployed as an immutable static site on GitHub Pages.

GitHub Pages cannot run a Python application at request time. In this project Python is used where it is most useful: it validates the structured professional profile, renders the website and printable CV, fingerprints assets, and produces a clean deployment artifact. The browser receives only semantic HTML, CSS, and a small progressive-enhancement script.

## What the build demonstrates

- Typed, validated content loaded from a single JSON source
- Deterministic rendering without a framework or runtime dependency
- Content escaping and HTTPS URL validation
- SHA-256 asset fingerprinting for reliable caching
- Atomic output generation with guarded build paths
- SEO metadata, JSON-LD, sitemap, robots file, and a custom 404 page
- Accessible navigation, reduced-motion support, responsive layouts, and print-ready CV styles
- Automated semantic and internal-link checks before deployment
- A GitHub Actions Pages pipeline that publishes only `dist/`

## Local development

Python 3.9 or newer is sufficient; there are no packages to install.

```bash
make validate
make test
make build
make serve
```

The preview is available at <http://127.0.0.1:8000>.

Equivalent direct commands are:

```bash
python3 -m portfolio_site validate
python3 -m portfolio_site build --output dist
python3 -m portfolio_site serve --port 8000
```

## Updating the profile

All public profile information lives in [`content/profile.json`](content/profile.json). Update that file to change roles, project cards, expertise, articles, credentials, or public links. Both the homepage and `/cv/` are generated from it, preventing the two views from drifting apart.

The curated Medium snapshot is intentionally committed as data. The production build never depends on a live third-party API, so a Medium or GitHub outage cannot break deployment.

## Project structure

```text
content/profile.json       Professional profile and CV data
portfolio_site/            Typed loader, renderer, builder, and CLI
templates/base.html        Shared HTML document shell
static/                    Source CSS, JavaScript, and vector assets
tests/                     Build, content, HTML, and link checks
.github/workflows/         CI and GitHub Pages deployment
dist/                      Generated artifact (ignored by Git)
```

## Deployment

Pushes to `master` run validation, tests, and the production build before deploying `dist/` through GitHub Pages. Pull requests run the same quality gate without deploying.

In the repository settings, set **Pages → Build and deployment → Source** to **GitHub Actions** once. No secrets, backend, analytics, or third-party JavaScript are required.

## Legacy site

The previous website currently lives in the local `legacy/` directory and is excluded from both Git and the Pages artifact. Review its licensing and personal content before choosing to publish any part of it.
