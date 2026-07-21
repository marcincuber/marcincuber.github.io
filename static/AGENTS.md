# Frontend asset guidance

## Scope

These instructions apply to source files under `static/` and extend the
repository-level guidance.

The build fingerprints `styles.css` and `site.js`; edit only these source files and
rebuild instead of touching hashed copies in `dist/assets/`. SVG files here are also
source assets copied into the Pages artifact.

- Keep JavaScript a progressive enhancement: navigation and core content must work
  when scripts fail or are disabled.
- Preserve keyboard behavior, accessible names, visible focus states, sufficient
  contrast, reduced-motion handling, responsive layouts, and print CV rules.
- Prefer system fonts and local assets. Do not add trackers, analytics, remote fonts,
  or frontend frameworks without explicit direction.
- Avoid embedding profile facts in CSS, JavaScript, or SVG; public content belongs in
  `content/profile.json`.
- Keep asset output deterministic and compatible with modern evergreen browsers.

After an asset edit, run `make test` and `make build`. For visual changes, preview
the homepage, CV, 404 page, narrow viewport behavior, and print styles as relevant.
