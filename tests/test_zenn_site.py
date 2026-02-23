"""Tests for zenn.dev site configuration."""

from __future__ import annotations

from md_fetch.converter import convert_to_markdown
from md_fetch.sites import create_default_registry
from md_fetch.sites.zenn import ZennSiteConfig


_CFG = ZennSiteConfig()


class TestZennSiteConfigProperties:
    """Verify property values of ZennSiteConfig."""

    def test_name(self) -> None:
        assert _CFG.name == "zenn"

    def test_host_patterns(self) -> None:
        assert _CFG.host_patterns == ["zenn.dev"]

    def test_content_selector(self) -> None:
        assert _CFG.content_selector == "div.znc"

    def test_title_selector(self) -> None:
        assert (
            _CFG.title_selector
            == 'h1[class*="ArticleHeader_title"], article h1, h1'
        )

    def test_remove_selectors(self) -> None:
        assert _CFG.remove_selectors == [
            'div[class*="ArticleComments"]',
            'aside[class*="View_sidebarContainer"]',
            'div[class*="ArticleSidebar"]',
            'div[class*="ProfileCard"]',
            "a.header-anchor-link",
            'button[class*="copyButton"]',
            'button[class*="wrapButton"]',
            'button[class*="FollowButton"]',
        ]


class TestZennSiteConversion:
    """Integration tests: zenn.dev HTML -> Markdown conversion."""

    def test_title_from_css_modules_class(self) -> None:
        """Title extraction via [class*=ArticleHeader_title] partial match."""
        html = (
            '<h1 class="ArticleHeader_title__ab12c">Zenn Article Title</h1>'
            '<div class="znc">'
            "<p>Hello zenn</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Zenn Article Title"
        assert "Hello zenn" in result.markdown

    def test_title_from_article_h1(self) -> None:
        """Fallback: article h1."""
        html = (
            "<article><h1>Article Fallback Title</h1></article>"
            '<div class="znc">'
            "<p>content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Article Fallback Title"

    def test_title_from_bare_h1(self) -> None:
        """Fallback: bare h1."""
        html = (
            "<h1>Bare Title</h1>"
            '<div class="znc">'
            "<p>content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Bare Title"

    def test_missing_title(self) -> None:
        html = (
            '<div class="znc">'
            "<p>no title here</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == ""
        assert "no title here" in result.markdown

    def test_remove_copy_button(self) -> None:
        html = (
            '<div class="znc">'
            "<p>keep</p>"
            '<button class="copyButton__x9f2a">Copy</button>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "keep" in result.markdown
        assert "Copy" not in result.markdown

    def test_remove_comments(self) -> None:
        html = (
            '<div class="znc">'
            "<p>article body</p>"
            '<div class="ArticleComments__abc12">comments here</div>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "article body" in result.markdown
        assert "comments here" not in result.markdown

    def test_remove_sidebar(self) -> None:
        html = (
            '<aside class="View_sidebarContainer__xyz">'
            "<p>sidebar</p>"
            "</aside>"
            '<div class="znc">'
            "<p>main content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "main content" in result.markdown
        assert "sidebar" not in result.markdown

    def test_remove_follow_button(self) -> None:
        html = (
            '<div class="znc">'
            "<p>text</p>"
            '<button class="FollowButton__abc">Follow</button>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "text" in result.markdown
        assert "Follow" not in result.markdown

    def test_remove_wrap_button(self) -> None:
        html = (
            '<div class="znc">'
            "<p>code block</p>"
            '<button class="wrapButton__def">Wrap</button>'
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "code block" in result.markdown
        assert "Wrap" not in result.markdown

    def test_remove_anchor_link(self) -> None:
        html = (
            '<div class="znc">'
            "<h2>Section</h2>"
            '<a class="header-anchor-link">#</a>'
            "<p>content</p>"
            "</div>"
        )
        result = convert_to_markdown(html, _CFG)
        assert "Section" in result.markdown
        assert "#" not in result.markdown or "##" in result.markdown

    def test_full_zenn_article(self) -> None:
        """Realistic zenn.dev page structure with CSS Modules hashed classes."""
        html = (
            '<h1 class="ArticleHeader_title__a1b2c">Zenn Tips</h1>'
            '<aside class="View_sidebarContainer__x9y8z">'
            '<div class="ProfileCard__p1q2r">Author info</div>'
            "</aside>"
            '<div class="znc">'
            "<h2>Section 1</h2>"
            '<a class="header-anchor-link">#</a>'
            "<p>First paragraph.</p>"
            '<button class="copyButton__c3d4e">Copy</button>'
            "<h2>Section 2</h2>"
            "<p>Second paragraph.</p>"
            '<button class="wrapButton__f5g6h">Wrap</button>'
            '<div class="ArticleComments__i7j8k">User comments</div>'
            '<button class="FollowButton__l9m0n">Follow</button>'
            "</div>"
            '<div class="ArticleSidebar__o1p2q">Related articles</div>'
        )
        result = convert_to_markdown(html, _CFG)
        assert result.title == "Zenn Tips"
        assert "## Section 1" in result.markdown
        assert "First paragraph." in result.markdown
        assert "## Section 2" in result.markdown
        assert "Second paragraph." in result.markdown
        # Removed elements
        assert "Author info" not in result.markdown
        assert "Copy" not in result.markdown
        assert "Wrap" not in result.markdown
        assert "User comments" not in result.markdown
        assert "Follow" not in result.markdown
        assert "Related articles" not in result.markdown


class TestDefaultRegistry:
    """Tests for create_default_registry() with Zenn URLs."""

    def test_zenn_url_matches(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://zenn.dev/and_and/articles/8e4dc3a47e7873")
        assert config.name == "zenn"

    def test_zenn_url_with_query_params(self) -> None:
        registry = create_default_registry()
        config = registry.find("https://zenn.dev/user/articles/abc123?ref=feed")
        assert config.name == "zenn"
