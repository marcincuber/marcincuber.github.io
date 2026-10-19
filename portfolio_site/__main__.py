"""Command-line interface for building, validating and previewing the site."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .builder import PROJECT_ROOT, build_site
from .checks import CheckError, check_external_links, check_live_site
from .content import ContentError, Profile
from .medium import SyncError, sync_medium
from .reports import markdown_text, write_summary


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="portfolio-site",
        description="Build Marcin Cuber's dependency-free static portfolio.",
    )
    subcommands = command.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build", help="Generate the production site")
    build.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")

    validate = subcommands.add_parser("validate", help="Validate structured content")
    validate.add_argument(
        "--content", type=Path, default=PROJECT_ROOT / "content" / "profile.json"
    )

    serve = subcommands.add_parser("serve", help="Build and serve a local preview")
    serve.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
    serve.add_argument("--port", type=int, default=8000)

    sync = subcommands.add_parser("sync-medium", help="Refresh the saved Medium articles")
    sync.add_argument("--content", type=Path, default=PROJECT_ROOT / "content" / "profile.json")
    sync.add_argument("--feed-file", type=Path, help="Read a saved RSS feed instead of fetching it")
    sync.add_argument("--dry-run", action="store_true", help="Validate updates without saving them")
    sync.add_argument("--summary", type=Path, help="Append a Markdown change report")
    sync.add_argument("--github-output", type=Path, help="Write the Actions changed output")

    for name, help_text in (
        ("check-links", "Check external links in the generated site"),
        ("check-live", "Compare a deployed site with the local production build"),
    ):
        check = subcommands.add_parser(name, help=help_text)
        check.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
        check.add_argument("--site-url", help="Site base URL; defaults to the canonical URL")
        check.add_argument("--summary", type=Path, help="Append a Markdown check report")
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "sync-medium":
            sync_medium(args.content, feed_file=args.feed_file, dry_run=args.dry_run,
                        summary=args.summary, github_output=args.github_output)
            return 0

        if args.command in {"check-links", "check-live"}:
            site_url = args.site_url or Profile.load(
                PROJECT_ROOT / "content" / "profile.json"
            ).site.canonical_url
            check = check_external_links if args.command == "check-links" else check_live_site
            return 0 if check(args.output, site_url, args.summary) else 1

        if args.command == "validate":
            profile = Profile.load(args.content)
            print(f"Content valid: {profile.site.name} ({len(profile.projects)} projects)")
            return 0

        result = build_site(args.output)
        print(f"Built {len(result.files)} files in {result.output}")
        if args.command == "build":
            return 0

        handler = partial(SimpleHTTPRequestHandler, directory=str(result.output))
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
        print(f"Previewing {result.output} at http://127.0.0.1:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nPreview stopped")
        finally:
            server.server_close()
        return 0
    except (ContentError, SyncError, CheckError, OSError) as error:
        print(f"Error: {error}")
        if getattr(args, "summary", None) is not None:
            write_summary(args.summary,
                          f"## {args.command} failed\n\n{markdown_text(str(error))}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
