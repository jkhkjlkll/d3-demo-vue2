#!/usr/bin/env python3
"""Build a portable HTML dashboard from backend data and a natural-language prompt."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "dashboard.template.html"
DEFAULT_MOCK_FILE = SKILL_DIR / "assets" / "mock_data.json"

HEALTH_ALIAS_TO_KEY = {
    "正常": "ok",
    "ok": "ok",
    "healthy": "ok",
    "告警": "warn",
    "warn": "warn",
    "warning": "warn",
    "异常": "err",
    "err": "err",
    "error": "err",
}

HEALTH_KEY_TO_DISPLAY = {
    "ok": "正常",
    "warn": "告警",
    "err": "异常",
}


@dataclass
class BuildContext:
    source: str
    raw_node_count: int
    raw_link_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dashboard from backend data + natural language")
    parser.add_argument("--api-url", default="", help="Backend endpoint returning graph JSON")
    parser.add_argument("--prompt", default="", help="Natural-language request used to infer filters")
    parser.add_argument("--output", default="./out/dashboard.html", help="Output HTML file path")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="HTML template file path")
    parser.add_argument("--mock-file", default=str(DEFAULT_MOCK_FILE), help="Mock data JSON path")
    parser.add_argument("--title", default="Ops Dashboard Skill Demo", help="Dashboard title")
    parser.add_argument("--timeout", type=float, default=6.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--strict-backend",
        action="store_true",
        help="Fail immediately when backend fetch fails (no mock fallback)",
    )
    return parser.parse_args()


def read_json_file(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def fetch_backend_json(api_url: str, timeout: float) -> Dict:
    req = Request(api_url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def normalize_health_display(value: str) -> str:
    key = HEALTH_ALIAS_TO_KEY.get(str(value).strip().lower(), "ok")
    return HEALTH_KEY_TO_DISPLAY[key]


def normalize_node(raw: Dict) -> Dict | None:
    node_id = str(raw.get("id", "")).strip()
    if not node_id:
        return None

    node = {
        "id": node_id,
        "label": str(raw.get("label", node_id)),
        "type": str(raw.get("type", "unknown")).strip().lower() or "unknown",
        "health": normalize_health_display(str(raw.get("health", "正常"))),
        "project": str(raw.get("project", "UNKNOWN")).strip() or "UNKNOWN",
    }
    return node


def normalize_link(raw: Dict) -> Dict | None:
    source = str(raw.get("source", "")).strip()
    target = str(raw.get("target", "")).strip()
    if not source or not target:
        return None
    return {
        "source": source,
        "target": target,
        "type": str(raw.get("type", "unknown")).strip().lower() or "unknown",
    }


def normalize_payload(payload: Dict) -> Dict[str, List[Dict]]:
    data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
    nodes_raw = data.get("nodes", []) if isinstance(data, dict) else []
    links_raw = data.get("links", []) if isinstance(data, dict) else []

    nodes = [n for n in (normalize_node(item or {}) for item in nodes_raw) if n]
    node_ids = {n["id"] for n in nodes}
    links = [l for l in (normalize_link(item or {}) for item in links_raw) if l and l["source"] in node_ids and l["target"] in node_ids]
    return {"nodes": nodes, "links": links}


def key_to_health(key: str) -> str:
    return HEALTH_KEY_TO_DISPLAY.get(key, "正常")


def health_to_key(display: str) -> str:
    return HEALTH_ALIAS_TO_KEY.get(str(display).strip().lower(), "ok")


def infer_keyword(prompt: str) -> str:
    explicit = re.search(r"(?:关键词|关键字|搜索|查找)\s*[:：]?\s*([^\n,，;；]+)", prompt, flags=re.I)
    if explicit:
        return explicit.group(1).strip()[:80]
    quoted = re.search(r"[\"“]([^\"”]{1,80})[\"”]", prompt)
    if quoted:
        return quoted.group(1).strip()[:80]
    return ""


def infer_filters_from_prompt(prompt: str, projects: Iterable[str]) -> Dict[str, str]:
    filters = {
        "project": "all",
        "entityType": "all",
        "relationType": "all",
        "health": "all",
        "keyword": "",
    }
    text = str(prompt or "").strip()
    if not text:
        return filters

    low = text.lower()
    compact = re.sub(r"\s+", "", low)

    if re.search(r"全部项目|所有项目|跨项目|allprojects", compact):
        filters["project"] = "all"
    else:
        upper_text = text.upper()
        for proj in sorted(set(projects)):
            if proj and proj.upper() in upper_text:
                filters["project"] = proj
                break
        if filters["project"] == "all":
            if "电商" in text or "p1" in compact:
                filters["project"] = "P001"
            elif "金融" in text or "p2" in compact:
                filters["project"] = "P002"

    entity_hints = [
        ("api", ["api", "接口"]),
        ("service", ["服务", "微服务", "svc"]),
        ("db", ["数据库", "db", "mysql", "postgres", "oracle"]),
        ("middleware", ["中间件", "redis", "kafka", "mq", "es"]),
        ("compute", ["计算", "节点", "k8s", "vm"]),
        ("alarm", ["告警", "alarm"]),
        ("user", ["用户"]),
        ("domain", ["域名"]),
    ]
    for key, hints in entity_hints:
        if any(h in low for h in hints):
            filters["entityType"] = key
            break

    relation_hints = [
        ("access", ["访问"]),
        ("call", ["调用"]),
        ("lb", ["负载", "lb"]),
        ("host", ["承载", "部署到", "运行在"]),
        ("monitor", ["监控"]),
    ]
    for key, hints in relation_hints:
        if any(h in low for h in hints):
            filters["relationType"] = key
            break

    if re.search(r"异常|故障|error|err", low):
        filters["health"] = "err"
    elif re.search(r"告警|warn|warning", low):
        filters["health"] = "warn"
    elif re.search(r"正常|healthy|\bok\b", low):
        filters["health"] = "ok"

    filters["keyword"] = infer_keyword(text)
    return filters


def apply_filters(nodes: List[Dict], links: List[Dict], filters: Dict[str, str]) -> Tuple[List[Dict], List[Dict]]:
    keyword = filters.get("keyword", "").strip().lower()

    def match_node(node: Dict) -> bool:
        if filters.get("project", "all") != "all" and node.get("project") != filters["project"]:
            return False
        if filters.get("entityType", "all") != "all" and node.get("type") != filters["entityType"]:
            return False
        if filters.get("health", "all") != "all" and health_to_key(node.get("health", "正常")) != filters["health"]:
            return False
        if keyword and keyword not in node.get("label", "").lower() and keyword not in node.get("id", "").lower():
            return False
        return True

    filtered_nodes = [node for node in nodes if match_node(node)]
    node_ids = {node["id"] for node in filtered_nodes}

    def match_link(link: Dict) -> bool:
        if link.get("source") not in node_ids or link.get("target") not in node_ids:
            return False
        if filters.get("relationType", "all") != "all" and link.get("type") != filters["relationType"]:
            return False
        return True

    filtered_links = [link for link in links if match_link(link)]
    return filtered_nodes, filtered_links


def build_summary(nodes: List[Dict], links: List[Dict]) -> Dict:
    health_counter = {"ok": 0, "warn": 0, "err": 0}
    entity_counter: Dict[str, int] = {}
    projects = set()

    for node in nodes:
        projects.add(node.get("project", "UNKNOWN"))
        h = health_to_key(node.get("health", "正常"))
        health_counter[h] = health_counter.get(h, 0) + 1
        et = node.get("type", "unknown")
        entity_counter[et] = entity_counter.get(et, 0) + 1

    return {
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "projectCount": len(projects),
        "okCount": health_counter.get("ok", 0),
        "warnCount": health_counter.get("warn", 0),
        "errCount": health_counter.get("err", 0),
        "entityTypeCounts": entity_counter,
    }


def render_dashboard(template_path: Path, title: str, payload: Dict, output_path: Path) -> None:
    template = template_path.read_text(encoding="utf-8")
    rendered = template.replace("__DASHBOARD_TITLE__", title)
    rendered = rendered.replace("__PAYLOAD_JSON__", json.dumps(payload, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def load_source_data(args: argparse.Namespace) -> Tuple[Dict[str, List[Dict]], BuildContext]:
    if args.api_url:
        try:
            payload = fetch_backend_json(args.api_url, timeout=args.timeout)
            normalized = normalize_payload(payload)
            return normalized, BuildContext(source=f"backend:{args.api_url}", raw_node_count=len(normalized["nodes"]), raw_link_count=len(normalized["links"]))
        except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            if args.strict_backend:
                raise RuntimeError(f"backend fetch failed: {exc}") from exc
            print(f"[WARN] backend fetch failed, fallback to mock: {exc}", file=sys.stderr)

    mock_path = Path(args.mock_file).expanduser().resolve()
    payload = read_json_file(mock_path)
    normalized = normalize_payload(payload)
    return normalized, BuildContext(source=f"mock:{mock_path}", raw_node_count=len(normalized["nodes"]), raw_link_count=len(normalized["links"]))


def main() -> int:
    args = parse_args()

    try:
        normalized, ctx = load_source_data(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    projects = sorted({n.get("project", "UNKNOWN") for n in normalized["nodes"]})
    filters = infer_filters_from_prompt(args.prompt, projects)
    nodes, links = apply_filters(normalized["nodes"], normalized["links"], filters)
    summary = build_summary(nodes, links)

    payload = {
        "title": args.title,
        "prompt": args.prompt,
        "filters": filters,
        "summary": summary,
        "nodes": nodes,
        "links": links,
        "meta": {
            "source": ctx.source,
            "rawNodeCount": ctx.raw_node_count,
            "rawLinkCount": ctx.raw_link_count,
        },
    }

    output_path = Path(args.output).expanduser().resolve()
    template_path = Path(args.template).expanduser().resolve()

    try:
        render_dashboard(template_path, args.title, payload, output_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] render failed: {exc}", file=sys.stderr)
        return 3

    meta_path = output_path.parent / f"{output_path.stem}.meta.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "output": str(output_path),
        "meta": str(meta_path),
        "filters": filters,
        "summary": summary,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
