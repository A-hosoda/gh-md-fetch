"""Tests for md_fetch.fetcher.fetch_page."""

from __future__ import annotations

import pytest

from md_fetch.fetcher import (
    FetchError,
    FetchNetworkError,
    FetchTimeoutError,
    fetch_page,
)


class TestFetchPageNormal:
    """Happy-path scenarios."""

    def test_returns_html_string(self, local_server: str) -> None:
        html = fetch_page(f"{local_server}/static")
        assert isinstance(html, str)
        assert "<h1>Hello</h1>" in html

    def test_includes_js_rendered_content(self, local_server: str) -> None:
        html = fetch_page(f"{local_server}/js-rendered")
        assert "JS OK" in html


class TestFetchPageError:
    """Error scenarios — domain exceptions raised correctly."""

    def test_invalid_url_raises_fetch_error(self) -> None:
        with pytest.raises(FetchError):
            fetch_page("not-a-valid-url")

    def test_timeout_raises_timeout_error(self, local_server: str) -> None:
        with pytest.raises(FetchTimeoutError):
            fetch_page(f"{local_server}/slow", timeout_ms=1_000)

    def test_unreachable_host_raises_network_error(self) -> None:
        with pytest.raises(FetchNetworkError):
            fetch_page("http://192.0.2.1:1", timeout_ms=5_000)


class TestFetchPageBoundary:
    """Boundary / edge-case scenarios."""

    def test_redirect_returns_final_page(self, local_server: str) -> None:
        html = fetch_page(f"{local_server}/redirect")
        assert "<h1>Hello</h1>" in html
