"""Base class for site-specific content extraction configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SiteConfig(ABC):
    """Abstract base class defining the extraction contract for a single site."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def host_patterns(self) -> list[str]: ...

    @property
    @abstractmethod
    def content_selector(self) -> str: ...

    @property
    @abstractmethod
    def title_selector(self) -> str: ...

    @property
    @abstractmethod
    def remove_selectors(self) -> list[str]: ...

    @property
    def wait_until(self) -> str:
        """Playwright wait strategy. Override per site if needed."""
        return "networkidle"
