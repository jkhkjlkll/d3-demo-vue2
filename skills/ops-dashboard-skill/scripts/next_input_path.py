#!/usr/bin/env python3
"""Allocate a fresh MCP input JSON path for this skill.

Use this helper when the host file tool refuses to overwrite an existing file
without a prior read. The script prints a unique path under runtime/inbox/.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_INBOX_DIR = SKILL_DIR / "runtime" / "inbox"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a fresh MCP input JSON path")
    parser.add_argument("--dir", default=str(DEFAULT_INBOX_DIR), help="Directory used to store fresh input files")
    parser.add_argument("--prefix", default="mcp-input", help="Filename prefix")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = Path(args.dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    token = uuid4().hex[:8]
    path = target_dir / f"{args.prefix}-{stamp}-{token}.json"
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
