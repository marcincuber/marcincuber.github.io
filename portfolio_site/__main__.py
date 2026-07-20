"""Command-line interface for building, validating and previewing the site."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .builder import PROJECT_ROOT, build_site
from .content import ContentError, Profile


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
    return command


def main() -> int:
    args = parser().parse_args()
    try:
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
    except ContentError as error:
        print(f"Content error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
