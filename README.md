# Marcin Cuber — professional cloud engineering profile

A fast, dependency-free portfolio generated with Python and deployed as an immutable static site on GitHub Pages.

GitHub Pages cannot run a Python application at request time. In this project Python is used where it is most useful: it validates the structured professional profile, renders the website and printable CV, fingerprints assets, and produces a clean deployment artifact. The browser receives only semantic HTML, CSS, local images, and a small progressive-enhancement script.

## What the build demonstrates

- Typed, validated content loaded from a single JSON source
- Deterministic rendering without a framework or runtime dependency
- Content escaping and HTTPS URL validation
- SHA-256 asset fingerprinting for reliable caching
- Atomic output generation with guarded build paths
- SEO metadata, JSON-LD, sitemap, robots file, and a custom 404 page
- Accessible navigation, persistent light/dark themes, reduced-motion support, responsive layouts, and print-ready CV styles
- A deterministic, same-origin CV PDF generated from the profile at build time
- A single-source CUBE/R identity system with generated, fingerprinted favicon and social assets
- A faceted visual language built from the logo’s isometric geometry and three-face palette
- Automated semantic and internal-link checks before deployment
- A GitHub Actions Pages pipeline that publishes only `dist/`

## Local development

Python 3.14 or newer is required; there are no packages to install. The committed
`.python-version` selects Python 3.14 for compatible version managers.

```bash
make validate
make test
make build
make serve
```

The preview is available at <http://127.0.0.1:8000>.

Equivalent direct commands are:

```bash
python3.14 -m portfolio_site validate
python3.14 -m portfolio_site build --output dist
python3.14 -m portfolio_site serve --port 8000
```

## Updating the profile

All public profile information lives in [`content/profile.json`](content/profile.json). Update that file to change roles, project cards, open-source organisations and module catalogues, expertise, articles, credentials, or public links. Both the homepage and `/cv/` are generated from it, preventing the two views from drifting apart.

The Medium snapshot is committed as data. The production build never depends on a live third-party API.

## Syncing Medium articles

Run the standard-library Python sync script locally, then rebuild to preview:

```bash
make sync-medium
make build
git diff -- content/profile.json
```

The direct command is `python3.14 -m portfolio_site sync-medium`. It derives the
[Medium RSS feed](https://help.medium.com/hc/en-us/articles/214874118-Using-RSS-feeds-of-profiles-publications-and-topics)
from `site.medium_url`, refreshes article titles, publication dates, topics and plain-text
excerpts, and removes RSS tracking parameters from links. Feed entries replace saved
entries with the same Medium story ID, including links with different slugs or domains.
Recent entries are merged with the saved snapshot and trimmed to the newest **12**.
The feed is a recent window, so older saved entries are retained until displaced;
absence from the feed does not mean an article was deleted. New articles outside
that window cannot be discovered. The current feed may contain fewer than 12 articles.

Only `articles` is updated; `site.last_updated` remains the date of the last
human-authored profile update. Empty, malformed or unavailable feeds fail without
replacing the snapshot. Unchanged results do not rewrite the file. Local sync does
not commit, push or publish anything.

Fetches make up to three attempts for connection failures, HTTP 408/429 and server
errors, with a 30-second request timeout and backoff. `Retry-After` seconds and dates
are supported, with each wait capped at 30 seconds. Other client errors, invalid
feeds and oversized responses fail immediately.

```bash
python3.14 -m portfolio_site sync-medium --dry-run
python3.14 -m portfolio_site sync-medium --feed-file /path/to/medium.xml
python3.14 -m portfolio_site sync-medium --dry-run --summary /tmp/medium-report.md
```

The **Sync Medium, test and deploy portfolio** workflow runs every Monday at
**06:23 UTC**. To update immediately, open **Actions → Sync Medium, test and deploy
portfolio → Run workflow**, selecting `main`. Weekly and manual runs sync, validate,
test and build before committing changed article data and deploying the refreshed
Pages artifact in the same run. Scheduled runs with no changes skip artifact upload
and deployment; manual runs still deploy, allowing an explicit refresh or retry.
The Actions summary lists added and updated articles and entries displaced from
the 12-article selection, plus counts and an explicit no-change or failure result.
Displaced entries are not claimed to have been deleted from Medium.
This avoids depending on a second push-triggered run:
[commits made with `GITHUB_TOKEN` do not trigger push workflows](https://docs.github.com/en/actions/concepts/security/github_token).
The workflow uses the built-in token with `contents: write`; no Medium credentials
or personal access token are needed. Repository rules must allow that token to push
to `main`. Scheduled/manual triggers become available once the workflow is on the
repository's default branch (`main`). Manual runs on other branches are skipped.
Push and pull-request checks continue using the saved snapshot without fetching Medium.

## Automated website checks

The separate **Check external links** workflow runs every **Tuesday at 07:41 UTC**
and supports **Actions → Check external links → Run workflow**. It builds the site,
collects outbound HTTP/HTTPS links from the generated HTML, removes duplicate URLs
and fragments, and checks non-Medium links with four concurrent requests and bounded
retries. Medium links are checked serially, with a two-second pause between requests
across all Medium subdomains, to avoid bursts.

The job uses `macos-latest`, a standard GitHub-hosted runner that needs no self-hosted
infrastructure. GitHub documents that [macOS runners use a different cloud network
from Ubuntu/Windows runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#ip-addresses).
This is a trial mitigation for the Medium 403 responses seen from Ubuntu runners;
it must be verified in a fresh Actions run. It cannot guarantee Medium will accept
the macOS runner's requests. Local success does not prove hosted-runner access.

Every outbound link, including Medium, must respond successfully for the job to pass.
There are no Medium exclusions or non-blocking failure exceptions. HTTP 401/403 and
exhausted rate limits are reported as unverified and fail the check, because the
request could not establish that the link works. Redirects are followed; email links
and same-site links are excluded. Each result appears in the Actions summary.
RSS synchronization and post-deployment checks retain their existing failure rules.
The maintenance workflow is independent of deployment and does not block publishing.
Remote URL fragments and the contents of third-party pages are not checked.

The deployment job rebuilds the exact validated Git revision (including any Medium
sync commit), publishes the Pages artifact, then compares the live responses with
those deterministic build files. It checks the homepage, CV, PDF, sitemap, robots,
web manifest, custom 404 file and all generated assets. Hidden build markers are
excluded. Failed or stale responses are retried over four rounds, waiting 5, 10 and
20 seconds between rounds. Requests use a content digest query parameter and ask
caches to revalidate. The workflow fails and reports mismatches if the deployed
files still differ; this does not roll back an already completed deployment. The
check verifies the `404.html` file, not the server's routing for nonexistent URLs.

Both checks use the Python standard library and can run locally:

```bash
make check-links
make check-live
# Or compare a local preview against the generated files:
python3.14 -m portfolio_site check-live --site-url http://127.0.0.1:8000
# Save a report in addition to console output:
python3.14 -m portfolio_site check-links --summary /tmp/external-links.md
```

`make check-live` compares the current local build with the canonical public site;
unpublished local content changes will correctly produce mismatches. Both commands
exit nonzero on failed checks. Normal builds and tests remain offline.

## Project structure

```text
content/profile.json       Professional profile and CV data
portfolio_site/            Typed loader, renderer, builder, and CLI
portfolio_site/brand.py    Shared logo geometry and generated brand assets
portfolio_site/pdf.py      Dependency-free, deterministic CV PDF renderer
portfolio_site/medium.py   Local and scheduled Medium RSS synchronization
portfolio_site/checks.py   External-link and post-deployment checks
portfolio_site/network.py Bounded HTTP fetches and retry handling
templates/base.html        Shared HTML document shell
static/                    Source CSS, JavaScript, and local images
tests/                     Build, content, HTML, and link checks
.github/workflows/         CI and GitHub Pages deployment
dist/                      Generated artifact (ignored by Git)
```

The build renders `/cv/Marcin-Cuber-CV.pdf` directly from
`content/profile.json`. The generated PDF is part of `dist/`, not the repository,
so it stays aligned with the web CV without committing or manually refreshing a
derived binary.

## Deployment

Pushes to `main` run validation, tests, and the production build before deploying `dist/` through GitHub Pages. Pull requests run the same quality gate without deploying.

In the repository settings, set **Pages → Build and deployment → Source** to **GitHub Actions** once. No secrets, backend, analytics, or third-party JavaScript are required.

## Legacy site

The previous website currently lives in the local `legacy/` directory and is excluded from both Git and the Pages artifact. Review its licensing and personal content before choosing to publish any part of it.
