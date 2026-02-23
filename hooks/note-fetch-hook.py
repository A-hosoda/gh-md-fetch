#!/usr/bin/env python3
"""PreToolUse hook: fetch note.com articles via playwright proxy.

Intercepts WebFetch for note.com URLs, fetches rendered HTML through
playwright-http-server, converts to markdown via md_fetch pipeline,
and returns the content (blocking the original WebFetch).

Requires:
  - playwright-http-server running on port 19877
  - Run via project .venv/bin/python (for md_fetch imports)
"""

import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

PROXY_URL = "http://127.0.0.1:19877"
NOTE_HOSTS = {"note.com", "note.mu"}


def is_note_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(host == h or host.endswith(f".{h}") for h in NOTE_HOSTS)


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "reason": reason,
        }
    }


def is_proxy_available() -> bool:
    try:
        req = urllib.request.Request(PROXY_URL, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception:
        return False


def fetch_html(url: str, timeout_ms: int = 30_000) -> str:
    """Fetch rendered HTML from playwright proxy."""
    payload = json.dumps({"url": url, "timeout_ms": timeout_ms}).encode()
    req = urllib.request.Request(
        PROXY_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())

    if data.get("error"):
        raise RuntimeError(data["error"].get("message", "proxy error"))

    return data["html"]


def convert_to_md(html: str, url: str) -> str:
    """Convert HTML to markdown using md_fetch pipeline."""
    # Ensure project root is in sys.path for md_fetch imports
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    from md_fetch.converter import convert_to_markdown
    from md_fetch.sites import create_default_registry

    registry = create_default_registry()
    site = registry.find(url)
    result = convert_to_markdown(html, site)
    title = result.title or ""
    md = result.markdown
    return f"# {title}\n\n{md}" if title else md


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "WebFetch":
        sys.exit(0)

    url = data.get("tool_input", {}).get("url", "")
    if not is_note_url(url):
        sys.exit(0)

    if not is_proxy_available():
        # Proxy not running, let WebFetch try
        sys.exit(0)

    try:
        html = fetch_html(url)
        markdown = convert_to_md(html, url)
    except Exception as e:
        print(json.dumps(deny(
            f"playwright proxy fetch failed: {e}\n"
            "Start the server: .venv/bin/python hooks/playwright-http-server.py &"
        )))
        sys.exit(0)

    print(json.dumps(deny(
        f"note.com article fetched via playwright proxy:\n\n{markdown}"
    )))
    sys.exit(0)


if __name__ == "__main__":
    main()
