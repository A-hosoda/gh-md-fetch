"""Tests for md_fetch.fetcher.fetch_page."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from md_fetch.fetcher import (
    FetchError,
    FetchNetworkError,
    FetchTimeoutError,
    _convert_proxy_error,
    _fetch_via_proxy,
    _is_proxy_available,
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


# ---------------------------------------------------------------------------
# Proxy-related unit tests (all mocked, no real server needed)
# ---------------------------------------------------------------------------


class TestIsProxyAvailable:
    """Health check detection."""

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_returns_true_when_proxy_responds_ok(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"status": "ok"}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        assert _is_proxy_available() is True

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_returns_false_when_proxy_responds_bad_status(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"status": "error"}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        assert _is_proxy_available() is False

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_returns_false_on_connection_refused(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionRefusedError("Connection refused")

        assert _is_proxy_available() is False

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_returns_false_on_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")

        assert _is_proxy_available() is False


class TestConvertProxyError:
    """Proxy error dict to domain exception mapping."""

    def test_timeout_type_returns_fetch_timeout_error(self):
        err = _convert_proxy_error({"type": "timeout", "message": "timed out"})
        assert isinstance(err, FetchTimeoutError)
        assert "timed out" in str(err)

    def test_network_type_returns_fetch_network_error(self):
        err = _convert_proxy_error({"type": "network", "message": "net::ERR_FAILED"})
        assert isinstance(err, FetchNetworkError)

    def test_general_type_returns_fetch_error(self):
        err = _convert_proxy_error({"type": "general", "message": "something broke"})
        assert isinstance(err, FetchError)
        assert not isinstance(err, (FetchTimeoutError, FetchNetworkError))

    def test_unknown_type_returns_fetch_error(self):
        err = _convert_proxy_error({"type": "unknown", "message": "weird"})
        assert isinstance(err, FetchError)

    def test_missing_fields_uses_defaults(self):
        err = _convert_proxy_error({})
        assert isinstance(err, FetchError)
        assert "Unknown proxy error" in str(err)


class TestFetchViaProxy:
    """Proxy fetch via urllib."""

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_returns_html_on_success(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps(
            {"html": "<html>OK</html>", "error": None}
        ).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        result = _fetch_via_proxy("https://example.com", timeout_ms=30_000)
        assert result == "<html>OK</html>"

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_raises_fetch_timeout_on_proxy_timeout_error(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "html": None,
            "error": {"type": "timeout", "message": "Navigation timeout"},
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        with pytest.raises(FetchTimeoutError, match="Navigation timeout"):
            _fetch_via_proxy("https://example.com", timeout_ms=5_000)

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_raises_fetch_network_on_proxy_network_error(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "html": None,
            "error": {"type": "network", "message": "net::ERR_NAME_NOT_RESOLVED"},
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        with pytest.raises(FetchNetworkError):
            _fetch_via_proxy("https://example.com", timeout_ms=30_000)

    @patch("md_fetch.fetcher.urllib.request.urlopen")
    def test_raises_fetch_network_on_connection_failure(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with pytest.raises(FetchNetworkError, match="Proxy request failed"):
            _fetch_via_proxy("https://example.com", timeout_ms=30_000)


class TestFetchPageFallback:
    """Proxy-first fallback strategy in fetch_page."""

    @patch("md_fetch.fetcher._fetch_via_proxy")
    @patch("md_fetch.fetcher._is_proxy_available", return_value=True)
    def test_uses_proxy_when_available(self, mock_avail, mock_proxy):
        mock_proxy.return_value = "<html>proxy</html>"

        result = fetch_page("https://example.com")

        assert result == "<html>proxy</html>"
        mock_proxy.assert_called_once_with(
            "https://example.com", timeout_ms=30_000, wait_until="networkidle",
        )

    @patch("md_fetch.fetcher._fetch_via_playwright")
    @patch("md_fetch.fetcher._is_proxy_available", return_value=False)
    def test_falls_back_to_playwright_when_proxy_unavailable(
        self, mock_avail, mock_pw,
    ):
        mock_pw.return_value = "<html>direct</html>"

        result = fetch_page("https://example.com")

        assert result == "<html>direct</html>"
        mock_pw.assert_called_once_with(
            "https://example.com", timeout_ms=30_000, wait_until="networkidle",
        )

    @patch("md_fetch.fetcher._fetch_via_playwright")
    @patch("md_fetch.fetcher._fetch_via_proxy")
    @patch("md_fetch.fetcher._is_proxy_available", return_value=True)
    def test_proxy_error_propagates_without_fallback(
        self, mock_avail, mock_proxy, mock_pw,
    ):
        mock_proxy.side_effect = FetchTimeoutError("proxy timeout")

        with pytest.raises(FetchTimeoutError, match="proxy timeout"):
            fetch_page("https://example.com")

        # Should NOT fall back to direct Playwright
        mock_pw.assert_not_called()

    @patch("md_fetch.fetcher._fetch_via_proxy")
    @patch("md_fetch.fetcher._is_proxy_available", return_value=True)
    def test_passes_custom_timeout(self, mock_avail, mock_proxy):
        mock_proxy.return_value = "<html>ok</html>"

        fetch_page("https://example.com", timeout_ms=5_000)

        mock_proxy.assert_called_once_with(
            "https://example.com", timeout_ms=5_000, wait_until="networkidle",
        )

    @patch("md_fetch.fetcher._fetch_via_proxy")
    @patch("md_fetch.fetcher._is_proxy_available", return_value=True)
    def test_passes_custom_wait_until(self, mock_avail, mock_proxy):
        mock_proxy.return_value = "<html>ok</html>"

        fetch_page("https://example.com", wait_until="load")

        mock_proxy.assert_called_once_with(
            "https://example.com", timeout_ms=30_000, wait_until="load",
        )
