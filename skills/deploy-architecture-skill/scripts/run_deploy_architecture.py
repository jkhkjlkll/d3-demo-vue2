#!/usr/bin/env python3
"""Deterministic entrypoint for the deploy architecture skill."""

from __future__ import annotations

import argparse
from pathlib import Path

import architecture_session as live
import build_architecture as builder


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SESSION_DIR = SKILL_DIR / "runtime" / "default-session"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deploy architecture skill in deterministic live-session mode"
    )
    parser.add_argument("--prompt", required=True, help="Natural-language request")
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Live session directory")
    parser.add_argument(
        "--input-json",
        default=str(builder.DEFAULT_INPUT_JSON),
        help="Local JSON payload path; can be the original file returned by MCP, not necessarily runtime/mcp-input.json",
    )
    parser.add_argument("--title", default="Deploy Architecture Live Session", help="Dashboard title")
    parser.add_argument("--port", type=int, default=8766, help="Preferred local port for the live dashboard server")
    parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Open the live dashboard URL in the local default browser",
    )
    parser.add_argument("--poll-ms", type=int, default=1500, help="How often the page polls live session updates")
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=120,
        help="How many idle seconds to keep the background live-session server alive without browser requests",
    )
    return parser.parse_args()


def session_exists(session_dir: Path) -> bool:
    return (session_dir / live.SESSION_CONFIG_NAME).exists()


def main() -> int:
    args = parse_args()
    session_dir = Path(args.session_dir).expanduser().resolve()

    if not session_exists(session_dir):
        start_args = argparse.Namespace(
            input_json=args.input_json,
            prompt=args.prompt,
            title=args.title,
            session_dir=str(session_dir),
            port=args.port,
            open_browser=args.open_browser,
            poll_ms=args.poll_ms,
            idle_timeout=args.idle_timeout,
        )
        return live.command_start(start_args)

    update_args = argparse.Namespace(
        session_dir=str(session_dir),
        prompt=args.prompt,
        input_json=args.input_json,
    )
    return live.command_update(update_args)


if __name__ == "__main__":
    raise SystemExit(main())
