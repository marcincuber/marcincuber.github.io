# Template guidance

## Scope

These instructions apply to `templates/` and extend the repository-level guidance.

`base.html` is a `string.Template` document shell. Its placeholder names are an API
shared with `portfolio_site/builder.py`; update both sides together and ensure no
unsubstituted `$placeholder` reaches generated output.

Keep page-specific markup in `portfolio_site/render.py`. Preserve one document
title, one `main` landmark, one `h1`, `lang="en-GB"`, canonical and social metadata,
JSON-LD, the skip link, and source-order accessibility. Generated content must stay
escaped before substitution.

After a template edit, run `make test` and `make build`, then inspect all generated
HTML pages rather than only the homepage.
