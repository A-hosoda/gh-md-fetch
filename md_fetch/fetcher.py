"""Fetch rendered HTML from a URL using Playwright."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

_DEFAULT_TIMEOUT_MS = 30_000
_PROXY_URL = "http://127.0.0.1:19877"
_PROXY_HEALTH_TIMEOUT_S = 2


class FetchError(Exception):
    """Base exception for page fetch failures."""


class FetchTimeoutError(FetchError):
    """Raised when page navigation times out."""


class FetchNetworkError(FetchError):
    """Raised when a network-level error occurs (DNS, connection refused, etc.)."""


def _convert_playwright_error(exc: PlaywrightError) -> FetchError:
    """Convert a Playwright error into the appropriate domain exception."""
    msg = str(exc)
    if isinstance(exc, PlaywrightTimeoutError):
        return FetchTimeoutError(msg)
    if "net::ERR_" in msg:
        return FetchNetworkError(msg)
    return FetchError(msg)


def _convert_proxy_error(error_dict: dict) -> FetchError:
    """Convert a proxy error response dict into the appropriate domain exception."""
    error_type = error_dict.get("type", "general")
    message = error_dict.get("message", "Unknown proxy error")
    if error_type == "timeout":
        return FetchTimeoutError(message)
    if error_type == "network":
        return FetchNetworkError(message)
    return FetchError(message)


def _is_proxy_available() -> bool:
    """Check if the playwright-http-server proxy is running."""
    try:
        req = urllib.request.Request(_PROXY_URL, method="GET")
        with urllib.request.urlopen(req, timeout=_PROXY_HEALTH_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception:
        return False


def _fetch_via_proxy(url: str, *, timeout_ms: int) -> str:
    """Fetch a URL via the playwright-http-server proxy."""
    payload = json.dumps({"url": url, "timeout_ms": timeout_ms}).encode()
    req = urllib.request.Request(
        _PROXY_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Allow generous time for the proxy to complete the Playwright fetch
    http_timeout = max(timeout_ms / 1000 + 10, 60)
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError) as exc:
        raise FetchNetworkError(f"Proxy request failed: {exc}") from exc

    if data.get("error"):
        raise _convert_proxy_error(data["error"])

    return data["html"]


def _fetch_via_playwright(url: str, *, timeout_ms: int) -> str:
    """Fetch a URL directly using Playwright."""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                # networkidle waits for no network connections for 500ms,
                # which is the best heuristic for JS-rendered article pages.
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                return page.content()
            except PlaywrightError as exc:
                raise _convert_playwright_error(exc) from exc
            finally:
                browser.close()
    except PlaywrightError as exc:
        # Catches errors from sync_playwright() or chromium.launch()
        raise _convert_playwright_error(exc) from exc


def fetch_page(url: str, *, timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> str:
    """Fetch a URL and return the fully-rendered HTML.

    Tries the playwright-http-server proxy first. If the proxy is not
    available, falls back to launching Playwright directly.

    Args:
        url: The URL to fetch.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        The rendered HTML as a string.

    Raises:
        FetchTimeoutError: Navigation exceeded *timeout_ms*.
        FetchNetworkError: A network-level error occurred.
        FetchError: Any other Playwright error.
    """
    if _is_proxy_available():
        return _fetch_via_proxy(url, timeout_ms=timeout_ms)
    return _fetch_via_playwright(url, timeout_ms=timeout_ms)
