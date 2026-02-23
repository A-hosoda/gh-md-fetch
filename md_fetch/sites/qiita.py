"""Site configuration for qiita.com."""

from __future__ import annotations

from md_fetch.sites.base import SiteConfig


class QiitaSiteConfig(SiteConfig):
    """Extraction configuration for qiita.com articles."""

    @property
    def name(self) -> str:
        return "qiita"

    @property
    def host_patterns(self) -> list[str]:
        return ["qiita.com", "*.qiita.com"]

    @property
    def content_selector(self) -> str:
        return ".it-MdContent, .s-MdContent"

    @property
    def title_selector(self) -> str:
        return "h1.it-Header_title, .it-MdContent h1:first-child, article h1"

    @property
    def remove_selectors(self) -> list[str]:
        return [
            ".it-MdContent__tableOfContents",
            ".it-Footer",
            ".it-Reactions",
        ]
