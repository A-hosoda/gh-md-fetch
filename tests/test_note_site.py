"""Tests for note.com site configuration."""

from __future__ import annotations

import pytest

from md_fetch.converter import convert_to_markdown
from md_fetch.sites import create_default_registry
from md_fetch.sites.note import NoteSiteConfig


_CFG = NoteSiteConfig()


class TestNoteSiteConfigProperties:
    """Verify property values of NoteSiteConfig."""

    def test_name(self) -> None:
        assert _CFG.name == "note"

    def test_host_patterns(self) -> None:
        assert _CFG.host_patterns == ["note.com", "*.note.com", "note.mu", "*.note.mu"]

    def test_wait_until(self) -> None:
        assert _CFG.wait_until == "networkidle"

    def test_content_selector(self) -> None:
        assert _CFG.content_selector == ".note-common-styles__textnote-body"

    def test_title_selector(self) -> None:
        assert _CFG.title_selector == ".o-noteContentHeader__title, h1"

    def test_remove_selectors(self) -> None:
        assert _CFG.remove_selectors == [
            ".o-noteContentHeader__supplement",
            ".o-noteContentFooter",
            ".embed-card",
        ]


class TestNoteSiteConversion:
    """Integration tests: note.com HTML -> Markdown conversion."""

    def test_title_from_note_header(self) -> None:
        html = (
            '<div class="o-noteContentHeader__title">My Note Title</div>'
            '<div class="note-common-styles__textnote-body">'
            "<p>Hello note</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "My Note Title"
        assert "Hello note" in result.markdown

    def test_title_fallback_to_h1(self) -> None:
        html = (
            "<h1>Fallback Title</h1>"
            '<div class="note-common-styles__textnote-body">'
            "<p>content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Fallback Title"

    def test_missing_title(self) -> None:
        html = (
            '<div class="note-common-styles__textnote-body">'
            "<p>no title</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == ""
        assert "no title" in result.markdown

    def test_remove_supplement(self) -> None:
        html = (
            '<div class="note-common-styles__textnote-body">'
            "<p>keep</p>"
            '<div class="o-noteContentHeader__supplement">date info</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "keep" in result.markdown
        assert "date info" not in result.markdown

    def test_remove_footer(self) -> None:
        html = (
            '<div class="note-common-styles__textnote-body">'
            "<p>body</p>"
            '<div class="o-noteContentFooter">footer stuff</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "body" in result.markdown
        assert "footer stuff" not in result.markdown

    def test_remove_embed_card(self) -> None:
        html = (
            '<div class="note-common-styles__textnote-body">'
            "<p>text</p>"
            '<div class="embed-card">embedded</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "text" in result.markdown
        assert "embedded" not in result.markdown

    def test_full_note_article(self) -> None:
        """Realistic note.com page structure."""
        html = (
            '<div class="o-noteContentHeader__title">My Article</div>'
            '<div class="o-noteContentHeader__supplement">2024-01-01</div>'
            '<div class="note-common-styles__textnote-body">'
            "<h2>Section 1</h2>"
            "<p>First paragraph.</p>"
            '<div class="embed-card">external link</div>'
            "<h2>Section 2</h2>"
            "<p>Second paragraph.</p>"
            '<div class="o-noteContentFooter">likes and shares</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "My Article"
        assert "## Section 1" in result.markdown
        assert "First paragraph." in result.markdown
        assert "## Section 2" in result.markdown
        assert "Second paragraph." in result.markdown
        # Removed elements
        assert "external link" not in result.markdown
        assert "likes and shares" not in result.markdown


class TestDefaultRegistry:
    """Tests for create_default_registry()."""

    def test_note_url_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://note.com/user/n/abc123")
        assert config.name == "note"

    def test_note_subdomain_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://www.note.com/article")
        assert config.name == "note"

    def test_note_mu_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://note.mu/user/n/abc123")
        assert config.name == "note"

    def test_note_mu_subdomain_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://www.note.mu/article")
        assert config.name == "note"

    def test_unknown_site_raises(self) -> None:
        from md_fetch.sites import UnsupportedSiteError

        registry = create_default_registry()
        with pytest.raises(UnsupportedSiteError):
            registry.find("https://example.com/page")
