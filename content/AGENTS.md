# Profile content guidance

## Scope

These instructions apply to files under `content/` and extend the repository-level
guidance.

`profile.json` is the canonical public data source for the homepage, printable CV,
metadata, and JSON-LD. Do not duplicate profile facts in templates or render code.

## Content integrity

- Treat every role, period, metric, certification, qualification, recognition,
  article, and project claim as user-owned factual information. Do not infer or
  embellish missing details.
- Do not add client names, internal project names, contact details, or other private
  information without explicit approval.
- Keep all public URLs absolute and HTTPS; validation intentionally rejects other
  schemes.
- Article `date` values use `YYYY-MM-DD`, and articles must remain newest first.
- Career data must contain exactly one entry with `current: true`.
- At least three projects must have `featured: true`.
- Project repositories, open-source organisation and module URLs, article URLs, and
  social labels must remain unique.
- Project `accent` must use a token accepted by `portfolio_site/content.py`.

When changing the JSON schema, update the corresponding frozen dataclasses and
validation in `portfolio_site/content.py`, every affected renderer, and the tests.

After any content edit, run `make validate`, `make test`, and `make build`.
