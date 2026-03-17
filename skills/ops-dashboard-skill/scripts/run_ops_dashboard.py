#!/usr/bin/env python3
"""Deterministic entrypoint for the ops dashboard skill.

This wrapper forces agents to use the bundled scripts/template instead of
hand-writing HTML. It auto-selects:
- start: when no live session exists yet
- update: when a live session already exists
"""

from __future__ import annotations

import argparse
from pathlib import Path

import build_dashboard as builder
import dashboard_session as live


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SESSION_DIR = SKILL_DIR / "runtime" / "default-session"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ops dashboard skill in deterministic live-session mode")
    parser.add_argument("--prompt", required=True, help="Natural-language request")
    parser.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Live session directory")
    parser.add_argument("--api-url", default="", help="Backend endpoint returning graph JSON")
    parser.add_argument("--app-id", default="", help="Optional appId query parameter passed to backend API")
    parser.add_argument("--app-alias-file", default="", help="Optional JSON file mapping spoken app names to appId/app_user")
    parser.add_argument("--mock-file", default=str(builder.DEFAULT_MOCK_FILE), help="Mock data JSON path")
    parser.add_argument("--timeout", type=float, default=6.0, help="HTTP timeout seconds")
    parser.add_argument("--title", default="Ops Dashboard Live Session", help="Dashboard title")
    parser.add_argument("--port", type=int, default=8765, help="Preferred local port for the live dashboard server")
    parser.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Open the live dashboard URL in the local default browser",
    )
    parser.add_argument("--poll-ms", type=int, default=1500, help="How often the page polls live session updates")
    parser.add_argument(
        "--refresh-data",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh backend/mock data before applying the new prompt when updating an existing session",
    )
    parser.add_argument(
        "--strict-backend",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="If true, backend fetch failures stop execution instead of falling back",
    )
    return parser.parse_args()


def decide_strict_backend(value: bool | None, api_url: str, is_start: bool) -> bool | None:
    if value is not None:
        return bool(value)
    if api_url:
        return True
    if is_start:
        return False
    return None


def session_exists(session_dir: Path) -> bool:
    return (session_dir / live.SESSION_CONFIG_NAME).exists()


def main() -> int:
    args = parse_args()
    session_dir = Path(args.session_dir).expanduser().resolve()
    is_start = not session_exists(session_dir)
    strict_backend = decide_strict_backend(args.strict_backend, args.api_url, is_start=is_start)

    if is_start:
        start_args = argparse.Namespace(
            api_url=args.api_url,
            app_id=args.app_id,
            app_alias_file=args.app_alias_file,
            prompt=args.prompt,
            title=args.title,
            mock_file=args.mock_file,
            timeout=args.timeout,
            strict_backend=bool(strict_backend),
            session_dir=str(session_dir),
            port=args.port,
            open_browser=args.open_browser,
            poll_ms=args.poll_ms,
        )
        return live.command_start(start_args)

    update_args = argparse.Namespace(
        session_dir=str(session_dir),
        prompt=args.prompt,
        app_id=args.app_id,
        api_url=args.api_url,
        app_alias_file=args.app_alias_file,
        mock_file=args.mock_file,
        timeout=args.timeout,
        refresh_data=args.refresh_data,
        strict_backend=strict_backend,
    )
    return live.command_update(update_args)


if __name__ == "__main__":
    raise SystemExit(main())
