"""Tests for CLI entry point."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from md_fetch.cli import (
    _build_filename,
    _run,
    parse_args,
    save_markdown,
    slugify,
)
from md_fetch.converter import ConversionError, ConvertResult
from md_fetch.fetcher import FetchError, FetchTimeoutError
from md_fetch.sites import UnsupportedSiteError


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgsNormal:
    """Normal: argument parsing."""

    def test_url_only(self) -> None:
        args = parse_args(["https://note.com/article/123"])
        assert args.url == "https://note.com/article/123"

    def test_default_output_dir(self) -> None:
        args = parse_args(["https://note.com/article/123"])
        assert args.output == Path.home() / "Downloads"

    def test_output_flag_short(self, tmp_path: Path) -> None:
        args = parse_args(["https://note.com/a", "-o", str(tmp_path)])
        assert args.output == tmp_path

    def test_output_flag_long(self, tmp_path: Path) -> None:
        args = parse_args(["https://note.com/a", "--output", str(tmp_path)])
        assert args.output == tmp_path


class TestParseArgsError:
    """Error: missing required arguments."""

    def test_no_arguments(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            parse_args([])
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


class TestSlugifyNormal:
    """Normal: slug generation."""

    def test_ascii_title(self) -> None:
        assert slugify("Hello World") == "Hello-World"

    def test_japanese_title(self) -> None:
        result = slugify("日本語タイトル")
        assert result == "日本語タイトル"

    def test_mixed_title(self) -> None:
        result = slugify("Pythonで学ぶ機械学習")
        assert result == "Pythonで学ぶ機械学習"

    def test_special_characters_removed(self) -> None:
        result = slugify("Hello! @World# $Test%")
        assert result == "Hello-World-Test"

    def test_multiple_spaces_collapsed(self) -> None:
        assert slugify("Hello   World") == "Hello-World"


class TestSlugifyBoundary:
    """Boundary: edge cases for slugify."""

    def test_empty_string(self) -> None:
        assert slugify("") == "untitled"

    def test_whitespace_only(self) -> None:
        assert slugify("   ") == "untitled"

    def test_only_special_chars(self) -> None:
        assert slugify("!@#$%^&*()") == "untitled"

    def test_max_length_truncation(self) -> None:
        long_title = "a" * 100
        result = slugify(long_title, max_length=80)
        assert len(result) <= 80

    def test_max_length_short(self) -> None:
        result = slugify("Hello World", max_length=5)
        assert len(result) <= 5

    def test_trailing_hyphen_after_truncation(self) -> None:
        # "abcde-fgh" truncated to 6 -> "abcde-" -> should strip trailing hyphen
        result = slugify("abcde fgh", max_length=6)
        assert not result.endswith("-")

    def test_fullwidth_normalization(self) -> None:
        # Full-width "Ａ" should normalize to "A"
        result = slugify("\uff21\uff22\uff23")
        assert result == "ABC"


# ---------------------------------------------------------------------------
# _build_filename
# ---------------------------------------------------------------------------


class TestBuildFilename:
    """Normal: dated filename generation."""

    @patch("md_fetch.cli.date")
    def test_basic_filename(self, mock_date: object) -> None:
        mock_date.today.return_value = date(2025, 1, 15)  # type: ignore[attr-defined]
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)  # type: ignore[attr-defined]
        result = _build_filename("My Article")
        assert result == "2025-01-15-My-Article.md"

    @patch("md_fetch.cli.date")
    def test_empty_title(self, mock_date: object) -> None:
        mock_date.today.return_value = date(2025, 1, 15)  # type: ignore[attr-defined]
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)  # type: ignore[attr-defined]
        result = _build_filename("")
        assert result == "2025-01-15-untitled.md"

    @patch("md_fetch.cli.date")
    def test_japanese_title(self, mock_date: object) -> None:
        mock_date.today.return_value = date(2025, 3, 20)  # type: ignore[attr-defined]
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)  # type: ignore[attr-defined]
        result = _build_filename("日本語の記事")
        assert result == "2025-03-20-日本語の記事.md"


# ---------------------------------------------------------------------------
# save_markdown
# ---------------------------------------------------------------------------


class TestSaveMarkdownNormal:
    """Normal: file saving."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        saved = save_markdown("# Hello", tmp_path, "test.md")
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == "# Hello"

    def test_save_returns_correct_path(self, tmp_path: Path) -> None:
        saved = save_markdown("content", tmp_path, "output.md")
        assert saved == tmp_path / "output.md"


class TestSaveMarkdownError:
    """Error: expected exceptions."""

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "nonexistent"
        with pytest.raises(OSError, match="does not exist"):
            save_markdown("content", bad_dir, "test.md")


class TestSaveMarkdownBoundary:
    """Boundary: duplicate filename handling."""

    def test_duplicate_filename_gets_suffix(self, tmp_path: Path) -> None:
        (tmp_path / "test.md").write_text("first")
        saved = save_markdown("second", tmp_path, "test.md")
        assert saved == tmp_path / "test-1.md"
        assert saved.read_text(encoding="utf-8") == "second"

    def test_multiple_duplicates(self, tmp_path: Path) -> None:
        (tmp_path / "test.md").write_text("first")
        (tmp_path / "test-1.md").write_text("second")
        saved = save_markdown("third", tmp_path, "test.md")
        assert saved == tmp_path / "test-2.md"

    def test_empty_content(self, tmp_path: Path) -> None:
        saved = save_markdown("", tmp_path, "empty.md")
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == ""


# ---------------------------------------------------------------------------
# _run (integration)
# ---------------------------------------------------------------------------

_DUMMY_HTML = "<h1>Title</h1><article><p>Hello world</p></article>"
_DUMMY_RESULT = ConvertResult(title="Title", markdown="# Title\n\nHello world")


class TestRunNormal:
    """Normal: successful pipeline execution."""

    @patch("md_fetch.cli.fetch_page", return_value=_DUMMY_HTML)
    @patch("md_fetch.cli.convert_to_markdown", return_value=_DUMMY_RESULT)
    @patch("md_fetch.cli.date")
    def test_success_returns_zero(
        self, mock_date: object, _mock_convert: object, _mock_fetch: object, tmp_path: Path
    ) -> None:
        mock_date.today.return_value = date(2025, 1, 1)  # type: ignore[attr-defined]
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)  # type: ignore[attr-defined]
        code = _run(["https://note.com/article/1", "-o", str(tmp_path)])
        assert code == 0

    @patch("md_fetch.cli.fetch_page", return_value=_DUMMY_HTML)
    @patch("md_fetch.cli.convert_to_markdown", return_value=_DUMMY_RESULT)
    @patch("md_fetch.cli.date")
    def test_creates_output_file(
        self, mock_date: object, _mock_convert: object, _mock_fetch: object, tmp_path: Path
    ) -> None:
        mock_date.today.return_value = date(2025, 1, 1)  # type: ignore[attr-defined]
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)  # type: ignore[attr-defined]
        _run(["https://note.com/article/1", "-o", str(tmp_path)])
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        assert files[0].read_text(encoding="utf-8") == _DUMMY_RESULT.markdown


class TestRunError:
    """Error: pipeline failure cases."""

    def test_unsupported_site(self, tmp_path: Path) -> None:
        code = _run(["https://unsupported.example.com/page", "-o", str(tmp_path)])
        assert code == 1

    @patch("md_fetch.cli.fetch_page", side_effect=FetchError("connection failed"))
    def test_fetch_error(self, _mock_fetch: object, tmp_path: Path) -> None:
        code = _run(["https://note.com/article/1", "-o", str(tmp_path)])
        assert code == 1

    @patch("md_fetch.cli.fetch_page", side_effect=FetchTimeoutError("timeout"))
    def test_fetch_timeout(self, _mock_fetch: object, tmp_path: Path) -> None:
        code = _run(["https://note.com/article/1", "-o", str(tmp_path)])
        assert code == 1

    @patch("md_fetch.cli.fetch_page", return_value=_DUMMY_HTML)
    @patch(
        "md_fetch.cli.convert_to_markdown",
        side_effect=ConversionError("no content found"),
    )
    def test_conversion_error(
        self, _mock_convert: object, _mock_fetch: object, tmp_path: Path
    ) -> None:
        code = _run(["https://note.com/article/1", "-o", str(tmp_path)])
        assert code == 1

    @patch("md_fetch.cli.fetch_page", return_value=_DUMMY_HTML)
    @patch("md_fetch.cli.convert_to_markdown", return_value=_DUMMY_RESULT)
    def test_output_dir_not_exists(
        self, _mock_convert: object, _mock_fetch: object, tmp_path: Path
    ) -> None:
        bad_dir = tmp_path / "nonexistent"
        code = _run(["https://note.com/article/1", "-o", str(bad_dir)])
        assert code == 1
