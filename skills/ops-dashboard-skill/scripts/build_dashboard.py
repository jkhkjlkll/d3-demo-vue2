#!/usr/bin/env python3
"""Build a portable HTML dashboard from backend data and a natural-language prompt."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "dashboard.template.html"
DEFAULT_MOCK_FILE = SKILL_DIR / "assets" / "mock_data.json"

HEALTH_ALIAS_TO_KEY = {
    "正常": "ok",
    "ok": "ok",
    "healthy": "ok",
    "normal": "ok",
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

ENTITY_ALIAS_TO_KEY = {
    "api": "api",
    "api接口": "api",
    "接口": "api",
    "service": "service",
    "应用微服务": "service",
    "服务": "service",
    "微服务": "service",
    "svc": "service",
    "db": "db",
    "database": "db",
    "数据库": "db",
    "middleware": "middleware",
    "中间件": "middleware",
    "compute": "compute",
    "计算": "compute",
    "计算资源": "compute",
    "node": "compute",
    "alarm": "alarm",
    "告警": "alarm",
    "user": "user",
    "用户": "user",
    "domain": "domain",
    "域名": "domain",
    "域名上下文根": "domain",
}

ENTITY_KEY_TO_DISPLAY = {
    "api": "API接口",
    "service": "应用微服务",
    "db": "数据库",
    "middleware": "中间件",
    "compute": "计算资源",
    "alarm": "告警",
    "user": "用户",
    "domain": "域名上下文根",
}

RELATION_ALIAS_TO_KEY = {
    "access": "access",
    "访问": "access",
    "call": "call",
    "调用": "call",
    "lb": "lb",
    "loadbalance": "lb",
    "负载": "lb",
    "负载均衡": "lb",
    "host": "host",
    "承载": "host",
    "部署": "host",
    "monitor": "monitor",
    "监控": "monitor",
}

RELATION_KEY_TO_DISPLAY = {
    "access": "访问",
    "call": "调用",
    "lb": "负载均衡",
    "host": "承载",
    "monitor": "监控",
}

ENTITY_COLOR_MAP = {
    "用户": "#4db8ff",
    "域名上下文根": "#00e5ff",
    "API接口": "#ff8c33",
    "应用微服务": "#00d68f",
    "数据库": "#ffcc00",
    "中间件": "#9d6fff",
    "计算资源": "#7fa8cc",
    "告警": "#ff4040",
}

RELATION_COLOR_MAP = {
    "访问": "#4db8ff",
    "调用": "#00d68f",
    "负载均衡": "#9d6fff",
    "承载": "#7fa8cc",
    "监控": "#ff4040",
}

FALLBACK_COLORS = [
    "#4db8ff",
    "#00d68f",
    "#9d6fff",
    "#ff8c33",
    "#00e5ff",
    "#ffcc00",
    "#7fa8cc",
    "#ff6666",
]

PROJECT_COLOR_THEMES = [
    {"color": "#1a9fff", "bgColor": "rgba(26,159,255,0.04)", "borderColor": "rgba(26,159,255,0.28)"},
    {"color": "#9d6fff", "bgColor": "rgba(157,111,255,0.04)", "borderColor": "rgba(157,111,255,0.28)"},
    {"color": "#00d68f", "bgColor": "rgba(0,214,143,0.04)", "borderColor": "rgba(0,214,143,0.28)"},
    {"color": "#ff8c33", "bgColor": "rgba(255,140,51,0.04)", "borderColor": "rgba(255,140,51,0.28)"},
    {"color": "#4db8ff", "bgColor": "rgba(77,184,255,0.04)", "borderColor": "rgba(77,184,255,0.28)"},
    {"color": "#ff6b6b", "bgColor": "rgba(255,107,107,0.04)", "borderColor": "rgba(255,107,107,0.28)"},
]

DEFAULT_LAYOUT = {
    "nodeWidth": 118,
    "nodeHeight": 42,
    "nodeVGap": 22,
    "bandMarginV": 28,
    "bandGap": 56,
    "canvasTop": 54,
    "colSpan": 168,
    "marginLeft": 90,
    "collapseThreshold": 20,
    "skillCollapseThreshold": 10,
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


def key_to_health(key: str) -> str:
    return HEALTH_KEY_TO_DISPLAY.get(key, "正常")


def health_to_key(display: str) -> str:
    return HEALTH_ALIAS_TO_KEY.get(str(display).strip().lower(), "ok")


def normalize_entity_key(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    return ENTITY_ALIAS_TO_KEY.get(raw.lower(), raw)


def normalize_relation_key(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    return RELATION_ALIAS_TO_KEY.get(raw.lower(), raw)


def key_to_entity_label(value: str) -> str:
    key = str(value or "").strip()
    return ENTITY_KEY_TO_DISPLAY.get(key, key or "未知")


def key_to_relation_label(value: str) -> str:
    key = str(value or "").strip()
    return RELATION_KEY_TO_DISPLAY.get(key, key or "未知")


def normalize_node(raw: Dict) -> Dict | None:
    node_id = str(raw.get("id") or raw.get("entity_id") or "").strip()
    if not node_id:
        return None

    node_type = normalize_entity_key(str(raw.get("type") or raw.get("entity_type") or "unknown"))
    project = str(raw.get("project") or raw.get("project_id") or "UNKNOWN").strip() or "UNKNOWN"

    return {
        "id": node_id,
        "label": str(raw.get("label") or raw.get("entity_name") or node_id),
        "type": node_type,
        "health": normalize_health_display(str(raw.get("health") or raw.get("health_status") or "正常")),
        "project": project,
    }


def normalize_link(raw: Dict) -> Dict | None:
    source = str(raw.get("source") or raw.get("source_entity_id") or "").strip()
    target = str(raw.get("target") or raw.get("target_entity_id") or "").strip()
    if not source or not target:
        return None
    return {
        "source": source,
        "target": target,
        "type": normalize_relation_key(str(raw.get("type") or raw.get("relation_type") or "unknown")),
        "health": normalize_health_display(str(raw.get("health") or raw.get("health_status") or "正常")),
    }


def normalize_payload(payload: Dict) -> Dict[str, List[Dict]]:
    data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
    nodes_raw = data.get("nodes", []) if isinstance(data, dict) else []
    if not isinstance(nodes_raw, list):
        nodes_raw = []

    links_raw = []
    if isinstance(data, dict):
        raw_links = data.get("links")
        raw_relations = data.get("relations")
        if isinstance(raw_links, list):
            links_raw = raw_links
        elif isinstance(raw_relations, list):
            links_raw = raw_relations

    nodes = [n for n in (normalize_node(item or {}) for item in nodes_raw) if n]
    node_ids = {n["id"] for n in nodes}
    links = [
        l
        for l in (normalize_link(item or {}) for item in links_raw)
        if l and l["source"] in node_ids and l["target"] in node_ids
    ]
    return {"nodes": nodes, "links": links}


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
        et = key_to_entity_label(node.get("type", "unknown"))
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


def pick_color(index: int, fallback_map: Dict[str, str], label: str) -> str:
    return fallback_map.get(label, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def build_project_config(projects: List[str]) -> List[Dict]:
    cfg = []
    for idx, project_id in enumerate(projects):
        theme = PROJECT_COLOR_THEMES[idx % len(PROJECT_COLOR_THEMES)]
        cfg.append(
            {
                "id": project_id,
                "name": project_id,
                "color": theme["color"],
                "bgColor": theme["bgColor"],
                "borderColor": theme["borderColor"],
            }
        )
    return cfg


def order_labels(labels: Iterable[str], known_order: List[str]) -> List[str]:
    known_index = {name: i for i, name in enumerate(known_order)}
    return sorted(set(labels), key=lambda x: (known_index.get(x, 999), x))


def build_type_config(labels: List[str], known_order: List[str], color_map: Dict[str, str]) -> List[Dict]:
    ordered = order_labels(labels, known_order)
    return [
        {
            "type": label,
            "color": pick_color(idx, color_map, label),
        }
        for idx, label in enumerate(ordered)
    ]


def worst_health(*values: str) -> str:
    level = {"正常": 0, "告警": 1, "异常": 2}
    normalized = [normalize_health_display(v) for v in values if v]
    if not normalized:
        return "正常"
    return max(normalized, key=lambda x: level.get(x, 0))


def to_graph_data(nodes: List[Dict], links: List[Dict]) -> Dict[str, List[Dict]]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    graph_nodes: List[Dict] = []
    node_health: Dict[str, str] = {}
    for node in nodes:
        health_display = normalize_health_display(node.get("health", "正常"))
        node_health[node["id"]] = health_display
        graph_nodes.append(
            {
                "entity_id": node["id"],
                "entity_name": node.get("label", node["id"]),
                "entity_type": key_to_entity_label(node.get("type", "unknown")),
                "project_id": node.get("project", "UNKNOWN"),
                "health_status": health_display,
                "created_at": now,
                "updated_at": now,
            }
        )

    graph_relations: List[Dict] = []
    for idx, link in enumerate(links, start=1):
        relation_health = worst_health(
            node_health.get(link.get("source", ""), "正常"),
            node_health.get(link.get("target", ""), "正常"),
            link.get("health", "正常"),
        )
        graph_relations.append(
            {
                "relation_id": f"R-{idx:05d}",
                "relation_type": key_to_relation_label(link.get("type", "unknown")),
                "source_entity_id": link.get("source"),
                "target_entity_id": link.get("target"),
                "health_status": relation_health,
                "created_at": now,
                "updated_at": now,
            }
        )

    return {"nodes": graph_nodes, "relations": graph_relations}


def build_app_config(graph_data: Dict[str, List[Dict]]) -> Dict:
    projects = sorted(
        {
            n.get("project_id")
            for n in graph_data.get("nodes", [])
            if n.get("project_id") and n.get("project_id") != "global"
        }
    )

    entity_labels = [n.get("entity_type", "未知") for n in graph_data.get("nodes", []) if n.get("entity_type")]
    relation_labels = [
        r.get("relation_type", "未知")
        for r in graph_data.get("relations", [])
        if r.get("relation_type")
    ]

    known_entity_order = [
        "用户",
        "域名上下文根",
        "API接口",
        "应用微服务",
        "数据库",
        "中间件",
        "计算资源",
        "告警",
    ]
    known_relation_order = ["访问", "调用", "负载均衡", "承载", "监控"]

    entity_types = build_type_config(entity_labels, known_entity_order, ENTITY_COLOR_MAP)
    relation_types = build_type_config(relation_labels, known_relation_order, RELATION_COLOR_MAP)

    if not entity_types:
        entity_types = build_type_config(known_entity_order, known_entity_order, ENTITY_COLOR_MAP)
    if not relation_types:
        relation_types = build_type_config(known_relation_order, known_relation_order, RELATION_COLOR_MAP)

    return {
        "projects": build_project_config(projects),
        "entityTypes": entity_types,
        "relationTypes": relation_types,
        "layout": DEFAULT_LAYOUT,
        "healthStates": ["正常", "正常", "正常", "告警", "异常"],
    }


def to_ui_filters(filters: Dict[str, str]) -> Dict[str, str]:
    return {
        "project": filters.get("project", "all"),
        "entityType": "all"
        if filters.get("entityType", "all") == "all"
        else key_to_entity_label(filters.get("entityType", "")),
        "relationType": "all"
        if filters.get("relationType", "all") == "all"
        else key_to_relation_label(filters.get("relationType", "")),
        "health": "all" if filters.get("health", "all") == "all" else key_to_health(filters.get("health", "ok")),
        "keyword": filters.get("keyword", ""),
    }


def render_dashboard(
    template_path: Path,
    title: str,
    graph_data: Dict,
    app_config: Dict,
    skill_state: Dict,
    legacy_payload: Dict,
    output_path: Path,
) -> None:
    template = template_path.read_text(encoding="utf-8")
    rendered = template.replace("__DASHBOARD_TITLE__", title)
    rendered = rendered.replace("__GRAPH_DATA_JSON__", json.dumps(graph_data, ensure_ascii=False))
    rendered = rendered.replace("__APP_CONFIG_JSON__", json.dumps(app_config, ensure_ascii=False))
    rendered = rendered.replace("__SKILL_STATE_JSON__", json.dumps(skill_state, ensure_ascii=False))
    rendered = rendered.replace("__PAYLOAD_JSON__", json.dumps(legacy_payload, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def load_source_data(args: argparse.Namespace) -> Tuple[Dict[str, List[Dict]], BuildContext]:
    if args.api_url:
        try:
            payload = fetch_backend_json(args.api_url, timeout=args.timeout)
            normalized = normalize_payload(payload)
            return normalized, BuildContext(
                source=f"backend:{args.api_url}",
                raw_node_count=len(normalized["nodes"]),
                raw_link_count=len(normalized["links"]),
            )
        except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            if args.strict_backend:
                raise RuntimeError(f"backend fetch failed: {exc}") from exc
            print(f"[WARN] backend fetch failed, fallback to mock: {exc}", file=sys.stderr)

    mock_path = Path(args.mock_file).expanduser().resolve()
    payload = read_json_file(mock_path)
    normalized = normalize_payload(payload)
    return normalized, BuildContext(
        source=f"mock:{mock_path}",
        raw_node_count=len(normalized["nodes"]),
        raw_link_count=len(normalized["links"]),
    )


def main() -> int:
    args = parse_args()

    try:
        normalized, ctx = load_source_data(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    projects = sorted({n.get("project", "UNKNOWN") for n in normalized["nodes"] if n.get("project")})
    filters = infer_filters_from_prompt(args.prompt, projects)
    filtered_nodes, filtered_links = apply_filters(normalized["nodes"], normalized["links"], filters)
    summary = build_summary(filtered_nodes, filtered_links)

    graph_data = to_graph_data(normalized["nodes"], normalized["links"])
    app_config = build_app_config(graph_data)
    ui_filters = to_ui_filters(filters)

    skill_state = {
        "prompt": args.prompt,
        "filters": ui_filters,
        "summary": summary,
        "meta": {
            "source": ctx.source,
            "rawNodeCount": ctx.raw_node_count,
            "rawLinkCount": ctx.raw_link_count,
        },
    }

    payload = {
        "title": args.title,
        "prompt": args.prompt,
        "filters": filters,
        "uiFilters": ui_filters,
        "summary": summary,
        "filtered": {
            "nodes": filtered_nodes,
            "links": filtered_links,
        },
        "dataset": {
            "nodes": normalized["nodes"],
            "links": normalized["links"],
        },
        "graphData": graph_data,
        "appConfig": app_config,
        "skillState": skill_state,
        "meta": {
            "source": ctx.source,
            "rawNodeCount": ctx.raw_node_count,
            "rawLinkCount": ctx.raw_link_count,
        },
    }

    output_path = Path(args.output).expanduser().resolve()
    template_path = Path(args.template).expanduser().resolve()

    try:
        render_dashboard(template_path, args.title, graph_data, app_config, skill_state, payload, output_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] render failed: {exc}", file=sys.stderr)
        return 3

    meta_path = output_path.parent / f"{output_path.stem}.meta.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output_path),
                "meta": str(meta_path),
                "filters": filters,
                "uiFilters": ui_filters,
                "summary": summary,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
