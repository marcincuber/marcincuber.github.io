# Python generator guidance

## Scope

These instructions apply to the `portfolio_site` package and extend the
repository-level guidance.

## Design constraints

- Preserve Python 3.14 compatibility and standard-library-only operation.
- `brand.py` owns shared identity geometry and deterministic SVG generation. Keep
  favicon, social-card, and inline lockups sourced from its common element set.
- `content.py` owns typed loading, local field checks, and cross-record invariants.
- `render.py` owns page fragments and structured data. Escape all profile-derived
  values at the rendering boundary; never interpolate untrusted content as raw HTML.
- `builder.py` owns template assembly, asset fingerprinting, auxiliary files, and
  atomic publication into the selected output directory.
- `__main__.py` owns the `validate`, `build`, and `serve` CLI surface. Keep errors
  concise and return a non-zero exit status for invalid content or failed builds.

The builder eventually calls `shutil.rmtree(output)` after path guards. Do not weaken
`_assert_safe_output`, symlink checks, staging cleanup, or atomic replacement. Tests
must cover any change to output-path handling.

Generated output must be byte-for-byte deterministic for identical inputs. Avoid
timestamps, unordered iteration, environment-dependent values, network access, and
machine-specific paths in generated files.

When changing rendering or the artifact shape, verify the homepage, CV, and 404
outputs and update `tests/test_site.py` to cover the new behavior. Run
`make validate`, `make test`, and `make build` before handoff.
