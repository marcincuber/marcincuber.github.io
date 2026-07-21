# Codex project guidance

## Scope

This file applies to the whole `marcincuber.github.io` repository. More specific
`AGENTS.md` files under `content/`, `portfolio_site/`, `templates/`, and `static/`
add rules for those areas.

## Project purpose

This repository is Marcin Cuber's public professional portfolio and printable CV.
It should demonstrate principal-level cloud engineering and cloud-native development
through both its content and its implementation quality.

GitHub Pages cannot execute Python at request time. Python is therefore a build-time
static-site generator; the deployed artifact is plain HTML, CSS, JavaScript, and SVG.
Keep the production site fast, accessible, deterministic, and independent of live
third-party APIs.

## Start every task here

1. Run `git status --short --branch` before changing files. Preserve unrelated user
   changes and never reset or clean the worktree without explicit permission.
2. Read `README.md`, `Makefile`, and the files relevant to the request.
3. Before modifying a directory with a nested `AGENTS.md`, read that file too.
4. Treat `content/profile.json` as the single source of professional-profile data.
5. Make changes in source files, then regenerate `dist/`; never hand-edit `dist/`.

The repository has previously been left on a detached `HEAD`, and its old tracked
site was replaced by the current generator while a local copy was retained under
ignored `legacy/`. Verify the current branch before any commit. Do not restore,
delete, publish, or otherwise modify `legacy/` unless Marcin explicitly asks.

## Architecture

```text
content/profile.json
        |
        v
portfolio_site/content.py   typed loading and validation
        |
        v
portfolio_site/render.py    homepage, CV, 404, and structured-data rendering
        |
        v
portfolio_site/builder.py   template assembly, asset hashing, atomic output
        |
        v
dist/                       generated GitHub Pages artifact
```

- `templates/base.html` is the shared HTML document shell.
- `static/` contains source CSS, progressive JavaScript, favicon, and social card.
- `tests/test_site.py` checks content invariants, semantic HTML, accessibility
  basics, links, asset hashes, canonical URLs, and deterministic builds.
- `.github/workflows/pages.yml` defines the authoritative CI and Pages deployment
  branch. It validates, tests, builds, and publishes only `dist/`.

## Canonical commands

Python 3.14 or newer is required. The generator has no runtime dependencies.

```bash
make validate
make test
make build
make serve
```

`make serve` rebuilds and serves the site at `http://127.0.0.1:8000`.
Equivalent direct commands are documented in `README.md`.

## Editing rules

- Keep public claims factual. Never invent roles, dates, metrics, qualifications,
  certifications, project ownership, or client details. Ask Marcin when a fact is
  ambiguous, and avoid confidential employer or customer information.
- Keep Python compatible with 3.14 and standard-library-only unless the task clearly
  justifies changing that architectural constraint.
- Preserve HTML escaping, absolute-HTTPS URL validation, deterministic rendering,
  SHA-256 asset fingerprinting, and guarded atomic output replacement.
- Keep the site useful with JavaScript disabled. Preserve semantic landmarks,
  keyboard access, visible focus, reduced-motion support, responsive layouts, and
  printable CV styling.
- Keep external dependencies, analytics, trackers, remote fonts, and live content
  fetches out of the production page unless explicitly requested.
- If a change adds a page or generated asset, update the sitemap/manifest/build and
  the artifact tests as appropriate.
- Do not commit, push, deploy, switch branches, or change GitHub repository settings
  unless the user explicitly requests it.

## Safe build boundary

`portfolio_site/builder.py` atomically replaces the selected output directory and
uses recursive deletion after safety checks. Use only repository `dist/` or a newly
created temporary directory as build output. Never pass an arbitrary existing
directory, the repository root, its parent, a home directory, or a symlink.

## Verification expectations

For any source or content change, run:

```bash
make validate
make test
make build
```

For visual changes, also inspect the generated homepage, `/cv/`, and `404.html` at
desktop and narrow widths when browser tooling is available. Check the printable CV
when altering layout or print CSS. Report exactly what was run and any checks that
could not be performed.

Before handing work back, inspect `git diff --check` and `git status --short`. Keep
generated `dist/`, macOS metadata, caches, and `legacy/` out of commits.
