#!/usr/bin/env python3
"""HTTP proxy server for Playwright page fetching.

Runs outside the Claude Code sandbox, executing Playwright to fetch
rendered HTML. This bypasses Chromium launch restrictions (network
and Mach port permissions) that occur inside the sandbox.

Usage:
  .venv/bin/python hooks/playwright-http-server.py &
  .venv/bin/python hooks/playwright-http-server.py --verbose

Endpoint: POST http://127.0.0.1:19877/
  Request:  {"url": "https://example.com", "timeout_ms": 30000}
  Response: {"html": "...", "error": null}
"""

import argparse
from datetime import datetime
import http.server
import json
import os
import signal
import sys

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

PORT = 19877
HOST = "127.0.0.1"

VERBOSE = False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="HTTP proxy server for Playwright page fetching",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print all requests and responses to stderr",
    )
    return parser.parse_args()


def log_verbose(msg: str):
    """Print verbose log with timestamp."""
    if VERBOSE:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}] {msg}", file=sys.stderr)


_VALID_WAIT_UNTIL = {"commit", "domcontentloaded", "load", "networkidle"}


def fetch_with_playwright(url: str, timeout_ms: int, wait_until: str = "networkidle") -> dict:
    """Fetch a URL with Playwright and return result dict.

    Returns:
        {"html": str, "error": None} on success, or
        {"html": None, "error": {"type": str, "message": str}} on failure.
    """
    if wait_until not in _VALID_WAIT_UNTIL:
        wait_until = "networkidle"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                html = page.content()
                return {"html": html, "error": None}
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        return {"html": None, "error": {"type": "timeout", "message": str(exc)}}
    except PlaywrightError as exc:
        msg = str(exc)
        error_type = "network" if "net::ERR_" in msg else "general"
        return {"html": None, "error": {"type": error_type, "message": msg}}
    except Exception as exc:
        return {"html": None, "error": {"type": "general", "message": str(exc)}}


class PlaywrightRelayHandler(http.server.BaseHTTPRequestHandler):
    """Handle Playwright fetch relay requests."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_POST(self):
        """Fetch a URL via Playwright and return rendered HTML."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            request = json.loads(body)
            url = request.get("url")
            timeout_ms = request.get("timeout_ms", 30_000)

            if not url:
                self._send_json(400, {
                    "html": None,
                    "error": {"type": "general", "message": "Missing 'url' field"},
                })
                return

            wait_until = request.get("wait_until", "networkidle")
            log_verbose(f">>> fetch {url} (timeout={timeout_ms}ms, wait={wait_until})")

            result = fetch_with_playwright(url, timeout_ms, wait_until)

            if result["error"]:
                log_verbose(f"<<< error: {result['error']}")
            else:
                html_len = len(result["html"]) if result["html"] else 0
                log_verbose(f"<<< ok ({html_len} chars)")

            self._send_json(200, result)

        except json.JSONDecodeError as e:
            self._send_json(400, {
                "html": None,
                "error": {"type": "general", "message": f"Invalid JSON: {e}"},
            })
        except Exception as e:
            self._send_json(500, {
                "html": None,
                "error": {"type": "general", "message": str(e)},
            })

    def do_GET(self):
        """Health check endpoint."""
        self._send_json(200, {"status": "ok", "service": "playwright-http-server"})

    def _send_json(self, status: int, data: dict):
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def main():
    global VERBOSE
    cli_args = parse_args()
    VERBOSE = cli_args.verbose

    pid_path = "/tmp/playwright-http-server.pid"
    with open(pid_path, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(signum=None, frame=None):
        try:
            os.unlink(pid_path)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    server = http.server.ThreadingHTTPServer((HOST, PORT), PlaywrightRelayHandler)
    print(
        f"playwright-http-server listening on http://{HOST}:{PORT} (PID {os.getpid()})",
        file=sys.stderr,
    )
    if VERBOSE:
        print("  Verbose mode: ON (logging all requests/responses)", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
