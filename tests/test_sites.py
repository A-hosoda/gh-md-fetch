"""Tests for site configuration registry."""

from __future__ import annotations

import pytest

from md_fetch.sites import SiteConfig, SiteRegistry, UnsupportedSiteError


class _DummySiteConfig(SiteConfig):
    """Concrete SiteConfig for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def host_patterns(self) -> list[str]:
        return ["note.com", "*.note.com"]

    @property
    def content_selector(self) -> str:
        return "article"

    @property
    def title_selector(self) -> str:
        return "h1"

    @property
    def remove_selectors(self) -> list[str]:
        return [".ads", ".sidebar"]


class _AnotherDummySiteConfig(SiteConfig):
    """Second concrete SiteConfig for priority testing."""

    @property
    def name(self) -> str:
        return "another"

    @property
    def host_patterns(self) -> list[str]:
        return ["*.note.com"]

    @property
    def content_selector(self) -> str:
        return "main"

    @property
    def title_selector(self) -> str:
        return "h2"

    @property
    def remove_selectors(self) -> list[str]:
        return []


@pytest.fixture()
def registry() -> SiteRegistry:
    reg = SiteRegistry()
    reg.register(_DummySiteConfig())
    return reg


class TestSiteRegistryNormal:
    """Normal: register + find."""

    def test_find_exact_host(self, registry: SiteRegistry) -> None:
        config = registry.find("https://note.com/article/123")
        assert config.name == "dummy"

    def test_find_returns_site_config_instance(self, registry: SiteRegistry) -> None:
        config = registry.find("https://note.com/")
        assert isinstance(config, SiteConfig)

    def test_register_multiple_configs(self, registry: SiteRegistry) -> None:
        registry.register(_AnotherDummySiteConfig())
        # Both registered, first match wins for exact host
        config = registry.find("https://note.com/")
        assert config.name == "dummy"


class TestSiteRegistryError:
    """Error: expected exceptions."""

    def test_unsupported_site(self, registry: SiteRegistry) -> None:
        with pytest.raises(UnsupportedSiteError, match="example.com"):
            registry.find("https://example.com/page")

    def test_empty_url(self, registry: SiteRegistry) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            registry.find("")

    def test_no_hostname(self, registry: SiteRegistry) -> None:
        with pytest.raises(ValueError, match="Could not extract hostname"):
            registry.find("not-a-url")


class TestSiteRegistryBoundary:
    """Boundary: edge-case URLs."""

    def test_subdomain_wildcard(self, registry: SiteRegistry) -> None:
        config = registry.find("https://www.note.com/article")
        assert config.name == "dummy"

    def test_url_with_path_and_query(self, registry: SiteRegistry) -> None:
        config = registry.find("https://note.com/path?q=1&r=2#frag")
        assert config.name == "dummy"

    def test_url_with_port(self, registry: SiteRegistry) -> None:
        config = registry.find("https://note.com:8080/page")
        assert config.name == "dummy"

    def test_first_registered_wins(self, registry: SiteRegistry) -> None:
        """When multiple configs match, the first registered config wins."""
        registry.register(_AnotherDummySiteConfig())
        # "www.note.com" matches both _DummySiteConfig and _AnotherDummySiteConfig
        config = registry.find("https://www.note.com/")
        assert config.name == "dummy"

    def test_abc_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            SiteConfig()  # type: ignore[abstract]


class TestWaitUntilDefault:
    """Default wait_until property."""

    def test_default_is_networkidle(self) -> None:
        config = _DummySiteConfig()
        assert config.wait_until == "networkidle"


class TestFindOrNone:
    """SiteRegistry.find_or_none behaviour."""

    def test_returns_config_for_known_host(self, registry: SiteRegistry) -> None:
        config = registry.find_or_none("https://note.com/article")
        assert config is not None
        assert config.name == "dummy"

    def test_returns_none_for_unknown_host(self, registry: SiteRegistry) -> None:
        assert registry.find_or_none("https://example.com/page") is None

    def test_returns_none_for_empty_url(self, registry: SiteRegistry) -> None:
        assert registry.find_or_none("") is None

    def test_returns_none_for_invalid_url(self, registry: SiteRegistry) -> None:
        assert registry.find_or_none("not-a-url") is None


class TestIsSupported:
    """SiteRegistry.is_supported behaviour."""

    def test_true_for_known_host(self, registry: SiteRegistry) -> None:
        assert registry.is_supported("https://note.com/article") is True

    def test_false_for_unknown_host(self, registry: SiteRegistry) -> None:
        assert registry.is_supported("https://example.com/page") is False

    def test_false_for_empty_url(self, registry: SiteRegistry) -> None:
        assert registry.is_supported("") is False

    def test_false_for_invalid_url(self, registry: SiteRegistry) -> None:
        assert registry.is_supported("not-a-url") is False
