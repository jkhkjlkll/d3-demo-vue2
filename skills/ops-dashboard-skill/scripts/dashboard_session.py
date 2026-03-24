#!/usr/bin/env python3
"""Live dashboard session manager.

Start a local dashboard once, then update filters/data without regenerating HTML.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
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
    start.add_argument(
        "--idle-timeout",
        type=int,
        default=120,
        help="How many idle seconds to keep the background HTTP server alive without browser requests",
    )

    update = subparsers.add_parser("update", help="Update prompt/filters for an existing session using the latest MCP JSON")
    update.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Directory storing live session files")
    update.add_argument("--prompt", default="", help="Natural-language request used to infer new filters")
    update.add_argument("--input-json", default="", help="Optional local JSON payload override for this update")

    serve = subparsers.add_parser("serve", help="Internal background HTTP server for a live session")
    serve.add_argument("--session-dir", required=True, help="Directory storing live session files")
    serve.add_argument("--port", type=int, required=True, help="Port to bind the local HTTP server")
    serve.add_argument(
        "--idle-timeout",
        type=int,
        default=120,
        help="How many idle seconds to keep the background HTTP server alive without browser requests",
    )

    stop = subparsers.add_parser("stop", help="Stop the background HTTP server for a live session")
    stop.add_argument("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Directory storing live session files")

    return parser.parse_args()


def add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input-json",
        default=str(builder.DEFAULT_INPUT_JSON),
        help="Local JSON payload path; can be the original file returned by MCP, not necessarily runtime/mcp-input.json",
    )
    parser.add_argument("--prompt", default="", help="Natural-language request used to infer filters")
    parser.add_argument("--title", default="Ops Dashboard Live Session", help="Dashboard title")


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


def terminate_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        result = subprocess.run(  # noqa: S603
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False

    for _ in range(20):
        if not is_pid_running(pid):
            return True
        sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return not is_pid_running(pid)

    for _ in range(20):
        if not is_pid_running(pid):
            return True
        sleep(0.1)
    return not is_pid_running(pid)


def start_server(session_dir: Path, port: int, idle_timeout: int) -> Tuple[int, Path]:
    log_path = session_dir / SESSION_LOG_NAME
    with log_path.open("ab") as log_fp:
        proc = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "serve",
                "--session-dir",
                str(session_dir),
                "--port",
                str(port),
                "--idle-timeout",
                str(max(5, int(idle_timeout))),
            ],
            stdout=log_fp,
            stderr=log_fp,
            start_new_session=True,
            cwd=tempfile.gettempdir(),
        )
    return proc.pid, log_path


def ensure_server_running(session_dir: Path, config: Dict[str, Any], preferred_port: int) -> Tuple[int, int, bool]:
    pid_file = session_dir / SESSION_PID_NAME
    current_pid = 0
    if pid_file.exists():
        try:
            current_pid = int(pid_file.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            current_pid = 0

    saved_port = int(config.get("port", preferred_port) or preferred_port)
    if is_pid_running(current_pid):
        return current_pid, saved_port, False

    port = pick_port(saved_port)
    idle_timeout = int(config.get("idle_timeout", 120) or 120)
    server_pid, _ = start_server(session_dir, port, idle_timeout)
    pid_file.write_text(str(server_pid), encoding="utf-8")
    return server_pid, port, True


def runtime_args_to_namespace(config: Dict) -> argparse.Namespace:
    return argparse.Namespace(
        input_json=config.get("input_json", ""),
    )


def build_payload(config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    normalized, ctx = builder.load_source_data(runtime_args_to_namespace(config))
    filters = builder.infer_filters_from_prompt(
        prompt,
        relation_types=[link.get("type", "") for link in normalized["links"]],
    )
    filtered_nodes, filtered_links = builder.apply_filters(normalized["nodes"], normalized["links"], filters)
    summary = builder.build_summary(filtered_nodes, filtered_links)
    graph_data = builder.to_graph_data(normalized["nodes"], normalized["links"])
    app_config = builder.build_app_config(graph_data)
    ui_filters = builder.to_ui_filters(filters)
    app_id = builder.derive_app_id(normalized["nodes"])

    return {
        "appId": app_id,
        "filters": filters,
        "uiFilters": ui_filters,
        "summary": summary,
        "graphData": graph_data,
        "appConfig": app_config,
        "meta": {
            "source": ctx.source,
            "rawNodeCount": ctx.raw_node_count,
            "rawLinkCount": ctx.raw_link_count,
            "appId": app_id,
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
        "liveSession": live_session,
    }

    meta_payload = {
        "title": config.get("title", "Ops Dashboard Live Session"),
        "prompt": prompt,
        "filters": payload["filters"],
        "uiFilters": payload["uiFilters"],
        "summary": payload["summary"],
        "appConfig": payload["appConfig"],
        "meta": payload["meta"],
        "liveSession": live_session,
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
        {"nodes": [], "relations": []},
        payload["appConfig"],
        bundle["skill_state"],
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


def command_serve(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir).expanduser().resolve()
    if not session_dir.exists():
        print(f"[ERROR] session directory not found: {session_dir}", file=sys.stderr)
        return 2

    idle_timeout = max(5, int(args.idle_timeout or 120))

    class LiveSessionHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *handler_args: Any, **handler_kwargs: Any) -> None:
            super().__init__(*handler_args, directory=str(session_dir), **handler_kwargs)

        def do_GET(self) -> None:  # noqa: N802
            self.server.last_activity = monotonic()  # type: ignore[attr-defined]
            super().do_GET()

        def do_HEAD(self) -> None:  # noqa: N802
            self.server.last_activity = monotonic()  # type: ignore[attr-defined]
            super().do_HEAD()

    class LiveSessionHTTPServer(http.server.ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    handler = functools.partial(LiveSessionHandler)
    with LiveSessionHTTPServer(("127.0.0.1", int(args.port)), handler) as server:
        server.timeout = 1
        server.last_activity = monotonic()  # type: ignore[attr-defined]
        while True:
            server.handle_request()
            if monotonic() - server.last_activity > idle_timeout:  # type: ignore[attr-defined]
                break
    return 0


def command_stop(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir).expanduser().resolve()
    pid_file = session_dir / SESSION_PID_NAME
    pid = 0
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            pid = 0

    stopped = terminate_pid(pid) if pid else False
    if pid_file.exists():
        pid_file.unlink(missing_ok=True)

    config_path = session_dir / SESSION_CONFIG_NAME
    if config_path.exists():
        config = read_json_file(config_path)
        config["server_pid"] = 0
        config["lastStoppedAt"] = now_iso()
        write_json_file(config_path, config)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": "stop",
                "sessionDir": str(session_dir),
                "stopped": bool(stopped or pid == 0 or not is_pid_running(pid)),
                "serverPid": pid,
            },
            ensure_ascii=False,
        )
    )
    return 0


def command_start(args: argparse.Namespace) -> int:
    session_dir = Path(args.session_dir).expanduser().resolve()
    session_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_json": str(Path(args.input_json or builder.DEFAULT_INPUT_JSON).expanduser().resolve()),
        "title": args.title,
        "poll_ms": args.poll_ms,
        "idle_timeout": max(5, int(args.idle_timeout or 120)),
    }

    try:
        payload = build_payload(config, args.prompt)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
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

    server_pid, port, _ = ensure_server_running(session_dir, config, args.port)

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
    if args.input_json:
        config["input_json"] = str(Path(args.input_json).expanduser().resolve())

    prompt = args.prompt or str(config.get("last_prompt", "")).strip()
    if not prompt:
        print("[ERROR] prompt is required for session update", file=sys.stderr)
        return 2

    try:
        payload = build_payload(config, prompt)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    current_version = int(config.get("version", 1))
    current_data_version = int(config.get("data_version", current_version))
    next_version = current_version + 1
    next_data_version = current_data_version + 1
    written = write_session_runtime_files(
        session_dir=session_dir,
        config=config,
        payload=payload,
        prompt=prompt,
        version=next_version,
        data_version=next_data_version,
        poll_ms=int(config.get("poll_ms", 1500)),
        refreshed_data=True,
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
    server_pid, port, restarted = ensure_server_running(session_dir, config, int(config.get("port", 8765) or 8765))
    config["server_pid"] = server_pid
    config["port"] = port
    config["url"] = f"http://127.0.0.1:{port}/{SESSION_HTML_NAME}"
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
                "refreshedData": True,
                "restartedServer": restarted,
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
    if args.command == "serve":
        return command_serve(args)
    if args.command == "stop":
        return command_stop(args)
    print(f"[ERROR] unsupported command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
