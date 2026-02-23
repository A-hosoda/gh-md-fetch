"""CLI entry point for gh-md-fetch."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from md_fetch.converter import ConversionError, convert_to_markdown
from md_fetch.fetcher import FetchError, fetch_page
from md_fetch.sites import UnsupportedSiteError, create_default_registry

_DEFAULT_OUTPUT_DIR = Path.home() / "Downloads"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with ``url`` and ``output`` attributes.
    """
    parser = argparse.ArgumentParser(
        prog="gh md-fetch",
        description="Fetch a web article and convert it to Markdown.",
    )
    parser.add_argument("url", help="URL of the article to fetch")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=(
            f"Output directory or file path (default: {_DEFAULT_OUTPUT_DIR}). "
            "If the path ends with .md, it is treated as a file path."
        ),
    )
    return parser.parse_args(argv)


def slugify(title: str, *, max_length: int = 80) -> str:
    """Convert a title into a filesystem-safe slug.

    Keeps CJK and alphanumeric characters, replaces unsafe chars with hyphens.
    Uses NFKC normalization. Returns "untitled" for empty input.

    Args:
        title: The article title.
        max_length: Maximum slug length.

    Returns:
        A filesystem-safe slug string.
    """
    if not title or not title.strip():
        return "untitled"

    # NFKC normalization (e.g. full-width -> half-width)
    text = unicodedata.normalize("NFKC", title.strip())

    # Replace any character that is not word-char or CJK with hyphen
    # \w covers [a-zA-Z0-9_] + Unicode letters/digits
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")

    if not text:
        return "untitled"

    return text[:max_length].rstrip("-")


def _build_filename(title: str) -> str:
    """Build a dated filename from a title.

    Format: ``YYYY-MM-DD-<slug>.md``
    """
    slug = slugify(title)
    return f"{date.today().isoformat()}-{slug}.md"


def save_markdown(content: str, output_dir: Path, filename: str) -> Path:
    """Save Markdown content to a file.

    If a file with the same name exists, appends a numeric suffix (-1, -2, ...).

    Args:
        content: Markdown text to write.
        output_dir: Directory to save into (must exist).
        filename: Base filename.

    Returns:
        The path of the saved file.

    Raises:
        OSError: If *output_dir* does not exist.
    """
    if not output_dir.is_dir():
        raise OSError(f"Output directory does not exist: {output_dir}")

    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".md"

    path = output_dir / filename
    counter = 1
    while path.exists():
        path = output_dir / f"{stem}-{counter}{suffix}"
        counter += 1

    path.write_text(content, encoding="utf-8")
    return path


def _run(argv: list[str] | None = None) -> int:
    """Run the URL-to-Markdown pipeline.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    args = parse_args(argv)

    registry = create_default_registry()
    try:
        site_config = registry.find(args.url)
    except (UnsupportedSiteError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        html = fetch_page(args.url, wait_until=site_config.wait_until)
    except FetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        result = convert_to_markdown(html, site_config)
    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path: Path = args.output
    if output_path.suffix == ".md":
        # Treat as a full file path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_path.write_text(result.markdown, encoding="utf-8")
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        saved = output_path
    else:
        # Treat as a directory
        filename = _build_filename(result.title)
        try:
            saved = save_markdown(result.markdown, output_path, filename)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    print(saved)
    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI entry point. Parses args, runs pipeline, and exits."""
    sys.exit(_run(argv))
