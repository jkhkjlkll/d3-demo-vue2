#!/usr/bin/env python3
"""Serve mock dashboard data over HTTP to simulate a backend API."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_MOCK_FILE = SKILL_DIR / "assets" / "mock_data.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mock backend for ops dashboard skill")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8787, help="Bind port")
    parser.add_argument("--mock-file", default=str(DEFAULT_MOCK_FILE), help="Mock JSON file path")
    return parser.parse_args()


def make_handler(payload_text: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str, content_type: str = "application/json; charset=utf-8") -> None:
            body_bytes = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body_bytes)

        def do_OPTIONS(self):  # noqa: N802
            self._send(200, "{}")

        def do_GET(self):  # noqa: N802
            if self.path in ("/health", "/healthz"):
                self._send(200, json.dumps({"status": "ok"}, ensure_ascii=False))
                return

            if self.path.startswith("/api/ops-graph"):
                self._send(200, payload_text)
                return

            self._send(404, json.dumps({"status": "error", "message": "not found"}, ensure_ascii=False))

        def log_message(self, fmt: str, *args):
            # Keep console output clean for agent logs.
            return

    return Handler


def main() -> int:
    args = parse_args()
    mock_path = Path(args.mock_file).expanduser().resolve()
    payload_text = mock_path.read_text(encoding="utf-8")

    # Validate JSON at startup.
    json.loads(payload_text)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(payload_text))
    print(f"Mock backend listening on http://{args.host}:{args.port}")
    print("Endpoints:")
    print(f"  GET http://{args.host}:{args.port}/api/ops-graph")
    print(f"  GET http://{args.host}:{args.port}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
      pass
    finally:
      server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
