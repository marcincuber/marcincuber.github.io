"""Plain Markdown reports for local commands and GitHub Actions summaries."""

from html import escape
from pathlib import Path
import re


def markdown_text(value: str) -> str:
    value = " ".join(value.split())
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>-])", r"\\\1", escape(value))


def write_summary(path: Path | None, report: str) -> None:
    print(report)
    if path is not None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(report + "\n\n")
