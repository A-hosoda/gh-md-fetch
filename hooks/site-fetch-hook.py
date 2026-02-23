#!/usr/bin/env python3
"""PreToolUse hook: fetch note.com / qiita.com articles via playwright proxy.

Intercepts WebFetch for supported sites, fetches rendered HTML through
playwright-http-server, converts to markdown via md_fetch pipeline,
saves the result to a temp file, and injects the file path into Claude's
context via additionalContext.

Requires:
  - playwright-http-server running on port 19877
  - Run via project .venv/bin/python (for md_fetch imports)
"""

import json
import sys
import tempfile
import urllib.request
from pathlib import Path

from md_fetch.sites import create_default_registry

PROXY_URL = "http://127.0.0.1:19877"

_registry = create_default_registry()


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
    site = _registry.find(url)
    payload = json.dumps({"url": url, "timeout_ms": timeout_ms, "wait_until": site.wait_until}).encode()
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


def convert_to_md(html: str, url: str) -> tuple[str, str, str]:
    """Convert HTML to markdown using md_fetch pipeline.

    Returns (markdown_with_title, title, site_name).
    """
    from md_fetch.converter import convert_to_markdown

    site = _registry.find(url)
    result = convert_to_markdown(html, site)
    title = result.title or ""
    md = f"# {title}\n\n{result.markdown}" if title else result.markdown
    return md, title, site.name


def save_markdown(markdown: str, title: str, site_name: str) -> Path:
    """Save markdown content to a temp file and return its path."""
    out_dir = Path(tempfile.gettempdir()) / "claude-md-fetch"
    out_dir.mkdir(exist_ok=True)
    slug = title[:50].replace("/", "-").replace(" ", "-") if title else "untitled"
    filename = f"{site_name}_{slug}.md"
    filepath = out_dir / filename
    filepath.write_text(markdown, encoding="utf-8")
    return filepath


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "WebFetch":
        sys.exit(0)

    url = data.get("tool_input", {}).get("url", "")
    if not _registry.is_supported(url):
        sys.exit(0)

    if not is_proxy_available():
        # Proxy not running, let WebFetch try
        sys.exit(0)

    try:
        html = fetch_html(url)
        markdown, title, site_name = convert_to_md(html, url)
        filepath = save_markdown(markdown, title, site_name)
    except Exception as e:
        # Fetch failed — deny with error context
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": (
                    f"[site-fetch-hook] Failed to fetch {url}: {e}\n"
                    "Ensure playwright-http-server is running: "
                    ".venv/bin/python ~/.claude/hooks/playwright-http-server.py &"
                ),
            }
        }))
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "additionalContext": (
                f"[site-fetch-hook] {site_name} article fetched successfully.\n"
                f"Title: {title}\n"
                f"Saved to: {filepath}\n"
                "Read this file to get the full article content."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
