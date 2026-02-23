"""Tests for qiita.com site configuration."""

from __future__ import annotations

from md_fetch.converter import convert_to_markdown
from md_fetch.sites import create_default_registry
from md_fetch.sites.qiita import QiitaSiteConfig


_CFG = QiitaSiteConfig()


class TestQiitaSiteConfigProperties:
    """Verify property values of QiitaSiteConfig."""

    def test_name(self) -> None:
        assert _CFG.name == "qiita"

    def test_host_patterns(self) -> None:
        assert _CFG.host_patterns == ["qiita.com", "*.qiita.com"]

    def test_content_selector(self) -> None:
        assert _CFG.content_selector == ".it-MdContent, .s-MdContent"

    def test_title_selector(self) -> None:
        assert (
            _CFG.title_selector
            == "h1.it-Header_title, .it-MdContent h1:first-child, article h1"
        )

    def test_remove_selectors(self) -> None:
        assert _CFG.remove_selectors == [
            ".it-MdContent__tableOfContents",
            ".it-Footer",
            ".it-Reactions",
        ]


class TestQiitaSiteConversion:
    """Integration tests: qiita.com HTML -> Markdown conversion."""

    def test_title_from_header(self) -> None:
        html = (
            '<h1 class="it-Header_title">Qiita Article Title</h1>'
            '<div class="it-MdContent">'
            "<p>Hello qiita</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Qiita Article Title"
        assert "Hello qiita" in result.markdown

    def test_title_from_content_h1(self) -> None:
        html = (
            '<div class="it-MdContent">'
            "<h1>Content Title</h1>"
            "<p>body text</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Content Title"

    def test_title_from_article_h1(self) -> None:
        html = (
            "<article><h1>Article Title</h1></article>"
            '<div class="it-MdContent">'
            "<p>content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Article Title"

    def test_missing_title(self) -> None:
        html = (
            '<div class="it-MdContent">'
            "<p>no title here</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == ""
        assert "no title here" in result.markdown

    def test_s_md_content_selector(self) -> None:
        html = (
            '<div class="s-MdContent">'
            "<p>alternative content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "alternative content" in result.markdown

    def test_remove_table_of_contents(self) -> None:
        html = (
            '<div class="it-MdContent">'
            "<p>keep</p>"
            '<div class="it-MdContent__tableOfContents">toc items</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "keep" in result.markdown
        assert "toc items" not in result.markdown

    def test_remove_footer(self) -> None:
        html = (
            '<div class="it-MdContent">'
            "<p>body</p>"
            '<div class="it-Footer">footer stuff</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "body" in result.markdown
        assert "footer stuff" not in result.markdown

    def test_remove_reactions(self) -> None:
        html = (
            '<div class="it-MdContent">'
            "<p>text</p>"
            '<div class="it-Reactions">likes</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "text" in result.markdown
        assert "likes" not in result.markdown

    def test_full_qiita_article(self) -> None:
        """Realistic qiita.com page structure."""
        html = (
            '<h1 class="it-Header_title">Python Tips</h1>'
            '<div class="it-MdContent">'
            '<div class="it-MdContent__tableOfContents">TOC</div>'
            "<h2>Section 1</h2>"
            "<p>First paragraph.</p>"
            "<h2>Section 2</h2>"
            "<p>Second paragraph.</p>"
            '<div class="it-Reactions">10 likes</div>'
            "</div>"
            '<div class="it-Footer">footer content</div>'
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Python Tips"
        assert "## Section 1" in result.markdown
        assert "First paragraph." in result.markdown
        assert "## Section 2" in result.markdown
        assert "Second paragraph." in result.markdown
        # Removed elements
        assert "TOC" not in result.markdown
        assert "10 likes" not in result.markdown
        assert "footer content" not in result.markdown


class TestDefaultRegistry:
    """Tests for create_default_registry() with Qiita URLs."""

    def test_qiita_url_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://qiita.com/user/items/abc123")
        assert config.name == "qiita"

    def test_qiita_subdomain_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://blog.qiita.com/article")
        assert config.name == "qiita"

    def test_qiita_url_with_query_params(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://qiita.com/user/items/abc123?ref=feed")
        assert config.name == "qiita"
