"""Tests for HTML-to-Markdown converter."""

from __future__ import annotations

import pytest

from md_fetch.converter import ConversionError, ConvertResult, convert_to_markdown
from md_fetch.sites.base import SiteConfig


class _DummySiteConfig(SiteConfig):
    """Concrete SiteConfig for converter tests."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def host_patterns(self) -> list[str]:
        return ["example.com"]

    @property
    def content_selector(self) -> str:
        return "article"

    @property
    def title_selector(self) -> str:
        return "h1"

    @property
    def remove_selectors(self) -> list[str]:
        return [".ads", "nav"]


_CFG = _DummySiteConfig()


class TestConvertNormal:
    """Normal: successful conversions."""

    def test_basic_paragraph(self) -> None:
        html = "<h1>Title</h1><article><p>Hello world</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert isinstance(result, ConvertResult)
        assert result.title == "Title"
        assert "Hello world" in result.markdown

    def test_heading_atx_style(self) -> None:
        html = "<h1>Title</h1><article><h2>Sub</h2><p>body</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert "## Sub" in result.markdown

    def test_code_block_with_language(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            '<pre><code class="language-python">print("hi")</code></pre>'
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "```python" in result.markdown
        assert 'print("hi")' in result.markdown

    def test_code_block_lang_prefix(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            '<pre><code class="lang-js">const x = 1;</code></pre>'
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "```js" in result.markdown

    def test_image_conversion(self) -> None:
        html = (
            "<h1>Title</h1>"
            '<article><img src="pic.png" alt="photo"></article>'
        )
        result = convert_to_markdown(html, _CFG)
        assert "![photo](pic.png)" in result.markdown

    def test_title_extraction(self) -> None:
        html = "<h1> My  Title </h1><article><p>body</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert result.title == "My  Title"

    def test_missing_title_element(self) -> None:
        html = "<article><p>No title here</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert result.title == ""
        assert "No title here" in result.markdown

    def test_link_conversion(self) -> None:
        html = '<h1>T</h1><article><a href="https://example.com">link</a></article>'
        result = convert_to_markdown(html, _CFG)
        assert "[link](https://example.com)" in result.markdown


class TestConvertError:
    """Error: expected exceptions."""

    def test_empty_html(self) -> None:
        with pytest.raises(ConversionError, match="empty"):
            convert_to_markdown("", _CFG)

    def test_whitespace_only_html(self) -> None:
        with pytest.raises(ConversionError, match="empty"):
            convert_to_markdown("   \n  ", _CFG)

    def test_content_selector_no_match(self) -> None:
        html = "<h1>Title</h1><div><p>Not an article</p></div>"
        with pytest.raises(ConversionError, match="content_selector"):
            convert_to_markdown(html, _CFG)


class TestConvertBoundary:
    """Boundary: edge cases and remove_selectors."""

    def test_remove_selectors_strips_ads(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            "<p>keep</p>"
            '<div class="ads">remove me</div>'
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "keep" in result.markdown
        assert "remove me" not in result.markdown

    def test_remove_selectors_strips_nav(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            "<nav><a>menu</a></nav>"
            "<p>content</p>"
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "menu" not in result.markdown
        assert "content" in result.markdown

    def test_nested_structure(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            "<div><div><p>deep</p></div></div>"
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "deep" in result.markdown

    def test_special_characters_preserved(self) -> None:
        html = "<h1>Title</h1><article><p>&amp; &lt; &gt; &quot;</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert "&" in result.markdown
        assert "<" in result.markdown
        assert ">" in result.markdown

    def test_excessive_blank_lines_collapsed(self) -> None:
        html = (
            "<h1>Title</h1>"
            "<article>"
            "<p>a</p><br><br><br><br><br><p>b</p>"
            "</article>"
        )
        result = convert_to_markdown(html, _CFG)
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in result.markdown

    def test_result_is_stripped(self) -> None:
        html = "<h1>Title</h1><article><p>text</p></article>"
        result = convert_to_markdown(html, _CFG)
        assert result.markdown == result.markdown.strip()

    def test_no_remove_selectors(self) -> None:
        """SiteConfig with empty remove_selectors works fine."""

        class _NoRemoveConfig(SiteConfig):
            @property
            def name(self) -> str:
                return "no-remove"

            @property
            def host_patterns(self) -> list[str]:
                return ["example.com"]

            @property
            def content_selector(self) -> str:
                return "main"

            @property
            def title_selector(self) -> str:
                return "h1"

            @property
            def remove_selectors(self) -> list[str]:
                return []

        html = '<h1>Title</h1><main><p>body</p><div class="ads">ad</div></main>'
        result = convert_to_markdown(html, _NoRemoveConfig())
        assert "body" in result.markdown
        assert "ad" in result.markdown
