"""Site configuration registry for md_fetch."""

from __future__ import annotations

from fnmatch import fnmatch
from urllib.parse import urlparse

from md_fetch.sites.base import SiteConfig

__all__ = ["SiteConfig", "SiteRegistry", "UnsupportedSiteError", "create_default_registry"]


class UnsupportedSiteError(Exception):
    """Raised when no registered SiteConfig matches the given URL."""


class SiteRegistry:
    """Registry that maps URLs to their SiteConfig by hostname pattern."""

    def __init__(self) -> None:
        self._configs: list[SiteConfig] = []

    def register(self, config: SiteConfig) -> None:
        """Register a site configuration."""
        self._configs.append(config)

    def find(self, url: str) -> SiteConfig:
        """Find the matching SiteConfig for a URL.

        Args:
            url: The URL to look up.

        Returns:
            The first matching SiteConfig.

        Raises:
            ValueError: If *url* is empty or has no extractable hostname.
            UnsupportedSiteError: If no registered config matches.
        """
        if not url:
            raise ValueError("url must not be empty")

        host = urlparse(url).hostname
        if not host:
            raise ValueError(f"Could not extract hostname from url: {url!r}")

        for config in self._configs:
            for pattern in config.host_patterns:
                if fnmatch(host, pattern):
                    return config

        raise UnsupportedSiteError(
            f"No site configuration found for host {host!r}"
        )

    def find_or_none(self, url: str) -> SiteConfig | None:
        """Find the matching SiteConfig, or return None on any failure."""
        try:
            return self.find(url)
        except (ValueError, UnsupportedSiteError):
            return None

    def is_supported(self, url: str) -> bool:
        """Return True if *url* matches any registered site."""
        return self.find_or_none(url) is not None


def create_default_registry() -> SiteRegistry:
    """Create a SiteRegistry pre-loaded with all built-in site configurations."""
    from md_fetch.sites.note import NoteSiteConfig
    from md_fetch.sites.qiita import QiitaSiteConfig

    registry = SiteRegistry()
    registry.register(NoteSiteConfig())
    registry.register(QiitaSiteConfig())
    return registry
