"""Site configuration for zenn.dev."""

from __future__ import annotations

from md_fetch.sites.base import SiteConfig


class ZennSiteConfig(SiteConfig):
    """Extraction configuration for zenn.dev articles."""

    @property
    def name(self) -> str:
        return "zenn"

    @property
    def host_patterns(self) -> list[str]:
        return ["zenn.dev"]

    @property
    def content_selector(self) -> str:
        return "div.znc"

    @property
    def title_selector(self) -> str:
        return 'h1[class*="ArticleHeader_title"], article h1, h1'

    @property
    def remove_selectors(self) -> list[str]:
        return [
            'div[class*="ArticleComments"]',
            'aside[class*="View_sidebarContainer"]',
            'div[class*="ArticleSidebar"]',
            'div[class*="ProfileCard"]',
            "a.header-anchor-link",
            'button[class*="copyButton"]',
            'button[class*="wrapButton"]',
            'button[class*="FollowButton"]',
        ]
