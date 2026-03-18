#!/usr/bin/env python3
"""Live dashboard session manager.

Start a local dashboard once, then update filters/data without regenerating HTML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import build_dashboard as builder


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SESSION_DIR = SKILL_DIR / "runtime" / "default-session"
SESSION_CONFIG_NAME = "session-config.json"
SESSION_CONTROL_NAME = "session-control.json"
SESSION_STATE_NAME = "session-state.json"
SESSION_HTML_NAME = "dashboard.html"
SESSION_META_NAME = "dashboard.meta.json"
SESSION_PID_NAME = "server.pid"
SESSION_LOG_NAME = "server.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage a live ops dashboard session")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Create a session, write HTML once, start local server, optionally open browser")
    add_common_runtime_args(start)
    start.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Directory storing live session files")
    start.add_argument("--port", type=int, default=8765, help="Preferred local port for the live dashboard server")
    start.add_argument(
        "--open-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Open the live dashboard URL in the default local browser",
    )
    start.add_argument("--poll-ms", type=int, default=1500, help="How often the page polls session control updates")

    update = subparsers.add_parser("update", help="Update prompt/filters and optionally refresh backend data for an existing session")
    update.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Directory storing live session files")
    update.add_argument("--prompt", default="", help="Natural-language request used to infer new filters")
    update.add_argument("--app-id", default="", help="Optional appId override for this update")
    update.add_argument("--api-url", default="", help="Optional API URL override for this update")
    update.add_argument("--input-json", default="", help="Optional local JSON payload override for this update")
    update.add_argument("--app-alias-file", default="", help="Optional alias file override for this update")
    update.add_argument("--mock-file", default="", help="Optional mock file override for this update")
    update.add_argument("--timeout", type=float, default=0.0, help="Optional timeout override for this update")
    update.add_argument(
        "--refresh-data",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh backend/mock data before applying the new prompt",
    )
    update.add_argument(
        "--strict-backend",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Optional strict-backend override for this update",
    )

    return parser.parse_args()


def add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-url", default="", help="Backend endpoint returning graph JSON")
    parser.add_argument(
        "--input-json",
        default="",
        help="Local JSON payload path (for MCP/external collectors); takes precedence over api/mock",
    )
    parser.add_argument("--app-id", default="", help="Optional appId query parameter passed to backend API")
    parser.add_argument("--app-alias-file", default="", help="Optional JSON file mapping spoken app names to appId/app_user values")
    parser.add_argument("--prompt", default="", help="Natural-language request used to infer filters")
    parser.add_argument("--title", default="Ops Dashboard Live Session", help="Dashboard title")
    parser.add_argument("--mock-file", default=str(builder.DEFAULT_MOCK_FILE), help="Mock data JSON path")
    parser.add_argument("--timeout", type=float, default=6.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--strict-backend",
        action="store_true",
        help="Fail immediately when backend fetch fails (no mock fallback)",
    )


def read_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_text_atomic(path: Path, content: str) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_template_signature() -> str:
    return file_sha256(builder.DEFAULT_TEMPLATE)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def pick_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


def open_browser(url: str) -> Tuple[bool, str]:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=True)
        elif sys.platform.startswith("win"):
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", url], check=True)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def start_server(session_dir: Path, port: int) -> Tuple[int, Path]:
    log_path = session_dir / SESSION_LOG_NAME
    with log_path.open("ab") as log_fp:
        proc = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "http.server",
                str(port),
                "--bind",
                "127.0.0.1",
                "--directory",
                str(session_dir),
            ],
            stdout=log_fp,
            stderr=log_fp,
            start_new_session=True,
        )
    return proc.pid, log_path


def runtime_args_to_namespace(config: Dict) -> argparse.Namespace:
    return argparse.Namespace(
        api_url=config.get("api_url", ""),
        input_json=config.get("input_json", ""),
        app_id=config.get("app_id", ""),
        timeout=config.get("timeout", 6.0),
        strict_backend=bool(config.get("strict_backend", False)),
        mock_file=config.get("mock_file", str(builder.DEFAULT_MOCK_FILE)),
    )


def build_payload(config: Dict[str, Any], prompt: str, app_aliases: Dict[str, str]) -> Dict[str, Any]:
    effective_app_id = str(config.get("app_id", "")).strip()
    if not effective_app_id:
        effective_app_id = builder.infer_app_id_from_prompt(prompt, app_aliases=app_aliases)

    runtime_config = dict(config)
    runtime_config["app_id"] = effective_app_id
    normalized, ctx = builder.load_source_data(runtime_args_to_namespace(runtime_config))

    projects = sorted({n.get("project", "UNKNOWN") for n in normalized["nodes"] if n.get("project")})
    filters = builder.infer_filters_from_prompt(
        prompt,
        projects,
        relation_types=[link.get("type", "") for link in normalized["links"]],
        app_aliases=app_aliases,
    )
    filtered_nodes, filtered_links = builder.apply_filters(normalized["nodes"], normalized["links"], filters)
    summary = builder.build_summary(filtered_nodes, filtered_links)
    graph_data = builder.to_graph_data(normalized["nodes"], normalized["links"])
    app_config = builder.build_app_config(graph_data)
    ui_filters = builder.to_ui_filters(filters)

    return {
        "appId": effective_app_id,
        "filters": filters,
        "uiFilters": ui_filters,
        "summary": summary,
        "graphData": graph_data,
        "appConfig": app_config,
        "normalized": normalized,
        "meta": {
            "source": ctx.source,
            "rawNodeCount": ctx.raw_node_count,
            "rawLinkCount": ctx.raw_link_count,
            "appId": effective_app_id,
        },
    }


def build_live_payload_bundle(
    config: Dict[str, Any],
    payload: Dict[str, Any],
    prompt: str,
    version: int,
    data_version: int,
    poll_ms: int,
    refreshed_data: bool,
) -> Dict[str, Dict[str, Any]]:
    live_session = {
        "enabled": True,
        "controlUrl": f"./{SESSION_CONTROL_NAME}",
        "stateUrl": f"./{SESSION_STATE_NAME}",
        "pollMs": poll_ms,
        "version": version,
        "dataVersion": data_version,
    }

    skill_state = {
        "prompt": prompt,
        "filters": payload["uiFilters"],
        "summary": payload["summary"],
        "meta": payload["meta"],
        "appAliases": config.get("app_aliases", {}),
        "liveSession": live_session,
    }

    meta_payload = {
        "title": config.get("title", "Ops Dashboard Live Session"),
        "prompt": prompt,
        "filters": payload["filters"],
        "uiFilters": payload["uiFilters"],
        "summary": payload["summary"],
        "dataset": payload["normalized"],
        "graphData": payload["graphData"],
        "appConfig": payload["appConfig"],
        "skillState": skill_state,
        "meta": payload["meta"],
        "updatedAt": now_iso(),
    }

    control_payload = {
        "version": version,
        "dataVersion": data_version,
        "prompt": prompt,
        "filters": payload["uiFilters"],
        "refreshedData": refreshed_data,
        "updatedAt": now_iso(),
    }

    state_payload = {
        "version": version,
        "dataVersion": data_version,
        "prompt": prompt,
        "filters": payload["uiFilters"],
        "summary": payload["summary"],
        "graphData": payload["graphData"],
        "appConfig": payload["appConfig"],
        "skillState": skill_state,
        "meta": payload["meta"],
        "updatedAt": now_iso(),
    }

    return {
        "meta": meta_payload,
        "control": control_payload,
        "state": state_payload,
        "skill_state": skill_state,
    }


def write_session_runtime_files(
    session_dir: Path,
    config: Dict[str, Any],
    payload: Dict[str, Any],
    prompt: str,
    version: int,
    data_version: int,
    poll_ms: int,
    refreshed_data: bool,
) -> Dict[str, Any]:
    meta_path = session_dir / SESSION_META_NAME
    control_path = session_dir / SESSION_CONTROL_NAME
    state_path = session_dir / SESSION_STATE_NAME

    bundle = build_live_payload_bundle(
        config=config,
        payload=payload,
        prompt=prompt,
        version=version,
        data_version=data_version,
        poll_ms=poll_ms,
        refreshed_data=refreshed_data,
    )

    write_json_file(meta_path, bundle["meta"])
    write_json_file(state_path, bundle["state"])
    write_json_file(control_path, bundle["control"])

    return {
        "metaPath": str(meta_path.resolve()),
        "controlPath": str(control_path.resolve()),
        "statePath": str(state_path.resolve()),
        "skillState": bundle["skill_state"],
    }


def render_session_html(
    session_dir: Path,
    config: Dict[str, Any],
    payload: Dict[str, Any],
    prompt: str,
    version: int,
    data_version: int,
    poll_ms: int,
) -> str:
    html_path = session_dir / SESSION_HTML_NAME
    bundle = build_live_payload_bundle(
        config=config,
        payload=payload,
        prompt=prompt,
        version=version,
        data_version=data_version,
        poll_ms=poll_ms,
        refreshed_data=True,
    )
    builder.render_dashboard(
        builder.DEFAULT_TEMPLATE,
        config.get("title", "Ops Dashboard Live Session"),
        payload["graphData"],
        payload["appConfig"],
        bundle["skill_state"],
        bundle["meta"],
        html_path,
    )
    return str(html_path.resolve())


def should_rebuild_html(config: Dict[str, Any], session_dir: Path) -> tuple[bool, str]:
    html_path = Path(str(config.get("html_path", session_dir / SESSION_HTML_NAME))).expanduser().resolve()
    if not html_path.exists():
        return True, "missing_html"

    saved_signature = str(config.get("template_signature", "")).strip()
    current_signature = current_template_signature()
    if not saved_signature:
        return True, "missing_template_signature"
    if saved_signature != current_signature:
        return True, "template_changed"
    return False, ""


def command_start(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir).expanduser().resolve()
    session_dir.mkdir(parents=True, exist_ok=True)

    app_aliases = builder.load_app_aliases(args.app_alias_file)
    config = {
        "api_url": args.api_url,
        "input_json": str(Path(args.input_json).expanduser().resolve()) if args.input_json else "",
        "app_id": args.app_id,
        "app_alias_file": str(Path(args.app_alias_file).expanduser().resolve()) if args.app_alias_file else "",
        "app_aliases": app_aliases,
        "mock_file": str(Path(args.mock_file).expanduser().resolve()),
        "timeout": args.timeout,
        "strict_backend": bool(args.strict_backend),
        "title": args.title,
        "poll_ms": args.poll_ms,
    }

    payload = build_payload(config, args.prompt, app_aliases)
    control_version = 1
    data_version = 1
    runtime_written = write_session_runtime_files(
        session_dir=session_dir,
        config=config,
        payload=payload,
        prompt=args.prompt,
        version=control_version,
        data_version=data_version,
        poll_ms=args.poll_ms,
        refreshed_data=True,
    )
    html_path = render_session_html(
        session_dir=session_dir,
        config=config,
        payload=payload,
        prompt=args.prompt,
        version=control_version,
        data_version=data_version,
        poll_ms=args.poll_ms,
    )

    pid_file = session_dir / SESSION_PID_NAME
    current_pid = 0
    if pid_file.exists():
        try:
            current_pid = int(pid_file.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            current_pid = 0

    if is_pid_running(current_pid):
        server_pid = current_pid
        port = int(read_json_file(session_dir / SESSION_CONFIG_NAME).get("port", args.port)) if (session_dir / SESSION_CONFIG_NAME).exists() else args.port
    else:
        port = pick_port(args.port)
        server_pid, _ = start_server(session_dir, port)
        pid_file.write_text(str(server_pid), encoding="utf-8")

    url = f"http://127.0.0.1:{port}/{SESSION_HTML_NAME}"
    session_config = {
        **config,
        "session_dir": str(session_dir),
        "port": port,
        "server_pid": server_pid,
        "url": url,
        "html_path": html_path,
        "template_path": str(builder.DEFAULT_TEMPLATE.resolve()),
        "template_signature": current_template_signature(),
        "version": control_version,
        "data_version": data_version,
        "last_prompt": args.prompt,
        "startedAt": now_iso(),
    }
    write_json_file(session_dir / SESSION_CONFIG_NAME, session_config)

    opened = False
    open_error = ""
    if args.open_browser:
        opened, open_error = open_browser(url)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": "start",
                "sessionDir": str(session_dir),
                "htmlPath": html_path,
                "metaPath": runtime_written["metaPath"],
                "url": url,
                "opened": opened,
                "openError": open_error,
            },
            ensure_ascii=False,
        )
    )
    return 0


def command_update(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir).expanduser().resolve()
    config_path = session_dir / SESSION_CONFIG_NAME
    if not config_path.exists():
        print(f"[ERROR] session config not found: {config_path}", file=sys.stderr)
        return 2

    config = read_json_file(config_path)
    if args.api_url:
        config["api_url"] = args.api_url
    if args.input_json:
        config["input_json"] = str(Path(args.input_json).expanduser().resolve())
    if args.app_id:
        config["app_id"] = args.app_id
    if args.mock_file:
        config["mock_file"] = str(Path(args.mock_file).expanduser().resolve())
    if args.timeout:
        config["timeout"] = args.timeout
    if args.strict_backend is not None:
        config["strict_backend"] = bool(args.strict_backend)
    if args.app_alias_file:
        config["app_alias_file"] = str(Path(args.app_alias_file).expanduser().resolve())

    app_aliases = builder.load_app_aliases(config.get("app_alias_file", ""))
    config["app_aliases"] = app_aliases

    prompt = args.prompt or str(config.get("last_prompt", "")).strip()
    if not prompt:
        print("[ERROR] prompt is required for session update", file=sys.stderr)
        return 2

    if args.refresh_data:
        payload = build_payload(config, prompt, app_aliases)
    else:
        existing_meta = read_json_file(session_dir / SESSION_META_NAME)
        payload = {
            "appId": config.get("app_id", ""),
            "filters": existing_meta.get("filters", {}),
            "uiFilters": existing_meta.get("uiFilters", {}),
            "summary": existing_meta.get("summary", {}),
            "graphData": existing_meta.get("graphData", {}),
            "appConfig": existing_meta.get("appConfig", {}),
            "normalized": existing_meta.get("dataset", {}),
            "meta": existing_meta.get("meta", {}),
        }
        projects = sorted({n.get("project", "UNKNOWN") for n in payload["normalized"].get("nodes", []) if n.get("project")})
        filters = builder.infer_filters_from_prompt(
            prompt,
            projects,
            relation_types=[link.get("type", "") for link in payload["normalized"].get("links", [])],
            app_aliases=app_aliases,
        )
        filtered_nodes, filtered_links = builder.apply_filters(payload["normalized"]["nodes"], payload["normalized"]["links"], filters)
        payload["filters"] = filters
        payload["uiFilters"] = builder.to_ui_filters(filters)
        payload["summary"] = builder.build_summary(filtered_nodes, filtered_links)

    current_version = int(config.get("version", 1))
    current_data_version = int(config.get("data_version", current_version))
    next_version = current_version + 1
    next_data_version = current_data_version + 1 if args.refresh_data else current_data_version
    written = write_session_runtime_files(
        session_dir=session_dir,
        config=config,
        payload=payload,
        prompt=prompt,
        version=next_version,
        data_version=next_data_version,
        poll_ms=int(config.get("poll_ms", 1500)),
        refreshed_data=bool(args.refresh_data),
    )
    rebuilt_html, rebuild_reason = should_rebuild_html(config, session_dir)
    if rebuilt_html:
        html_path = render_session_html(
            session_dir=session_dir,
            config=config,
            payload=payload,
            prompt=prompt,
            version=next_version,
            data_version=next_data_version,
            poll_ms=int(config.get("poll_ms", 1500)),
        )
        config["html_path"] = html_path
        config["template_path"] = str(builder.DEFAULT_TEMPLATE.resolve())
        config["template_signature"] = current_template_signature()

    config["version"] = next_version
    config["data_version"] = next_data_version
    config["last_prompt"] = prompt
    config["lastUpdatedAt"] = now_iso()
    if payload.get("appId"):
        config["app_id"] = payload["appId"]
    write_json_file(config_path, config)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": "update",
                "sessionDir": str(session_dir),
                "htmlPath": str(Path(config.get("html_path", session_dir / SESSION_HTML_NAME)).resolve()),
                "metaPath": written["metaPath"],
                "url": config.get("url", ""),
                "version": next_version,
                "dataVersion": next_data_version,
                "refreshedData": bool(args.refresh_data),
                "rebuiltHtml": rebuilt_html,
                "rebuildReason": rebuild_reason,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "start":
        return command_start(args)
    if args.command == "update":
        return command_update(args)
    print(f"[ERROR] unsupported command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
