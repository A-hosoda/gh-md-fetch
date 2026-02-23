"""Shared test fixtures — local HTTP server for fetcher tests."""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _Handler(BaseHTTPRequestHandler):
    """Minimal HTTP handler with routes for fetcher tests."""

    def do_GET(self) -> None:  # noqa: N802
        routes = {
            "/static": self._static,
            "/js-rendered": self._js_rendered,
            "/redirect": self._redirect,
            "/slow": self._slow,
        }
        handler = routes.get(self.path)
        if handler is None:
            self.send_error(404)
            return
        handler()

    def _static(self) -> None:
        body = b"<html><body><h1>Hello</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def _js_rendered(self) -> None:
        body = (
            b"<html><body>"
            b"<div id='root'></div>"
            b"<script>document.getElementById('root').textContent='JS OK';</script>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self) -> None:
        self.send_response(301)
        self.send_header("Location", "/static")
        self.end_headers()

    def _slow(self) -> None:
        time.sleep(60)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress request logs during tests
        pass


@pytest.fixture(scope="session")
def local_server():
    """Start a local HTTP server and yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
