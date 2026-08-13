"""Small read-only HTTP endpoint for aggregate call analytics."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from call_analytics import CallAnalyticsStore

logger = logging.getLogger(__name__)


class AnalyticsRequestHandler(BaseHTTPRequestHandler):
    """Serve only the aggregate analytics needed by the dashboard."""

    def do_GET(self) -> None:
        if self.path != "/api/analytics":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            store: CallAnalyticsStore = self.server.analytics_store  # type: ignore[attr-defined]
            self._send_json(HTTPStatus.OK, store.get_call_analytics())
        except sqlite3.Error:
            logger.exception("Call analytics database query failed")
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "Analytics are temporarily unavailable"},
            )

    def _send_json(self, status: HTTPStatus, body: dict[str, int | str]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, message_format: str, *args: object) -> None:
        logger.debug("Analytics API: " + message_format, *args)


def start_analytics_server(
    store: CallAnalyticsStore, host: str, port: int
) -> ThreadingHTTPServer | None:
    """Start the API alongside the agent worker without blocking LiveKit."""
    try:
        server = ThreadingHTTPServer((host, port), AnalyticsRequestHandler)
    except OSError:
        logger.exception("Call analytics API could not start on %s:%s", host, port)
        return None

    server.analytics_store = store  # type: ignore[attr-defined]
    server.daemon_threads = True
    threading.Thread(
        target=server.serve_forever,
        name="call-analytics-api",
        daemon=True,
    ).start()
    logger.info(
        "Call analytics API listening on http://%s:%s/api/analytics", host, port
    )
    return server
