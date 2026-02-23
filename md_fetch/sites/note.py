"""Site configuration for note.com."""

from __future__ import annotations

from md_fetch.sites.base import SiteConfig


class NoteSiteConfig(SiteConfig):
    """Extraction configuration for note.com articles."""

    @property
    def name(self) -> str:
        return "note"

    @property
    def host_patterns(self) -> list[str]:
        return ["note.com", "*.note.com"]

    @property
    def content_selector(self) -> str:
        return ".note-common-styles__textnote-body"

    @property
    def title_selector(self) -> str:
        return ".o-noteContentHeader__title, h1"

    @property
    def remove_selectors(self) -> list[str]:
        return [
            ".o-noteContentHeader__supplement",
            ".o-noteContentFooter",
            ".embed-card",
        ]
