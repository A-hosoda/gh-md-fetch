"""Fetch rendered HTML from a URL using Playwright."""

from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

_DEFAULT_TIMEOUT_MS = 30_000


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


def fetch_page(url: str, *, timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> str:
    """Fetch a URL and return the fully-rendered HTML.

    Launches a headless Chromium browser, navigates to *url*, waits for
    the network to become idle, and returns ``page.content()``.

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
