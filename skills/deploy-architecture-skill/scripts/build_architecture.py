#!/usr/bin/env python3
"""Build a portable HTML deployment architecture view from MCP JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "dashboard.template.html"
DEFAULT_INPUT_JSON = SKILL_DIR / "runtime" / "mcp-input.json"
INVALID_PROJECT_VALUES = {
    "cirelation",
}
SKILL_PROMPT_MARKERS = (
    "$deploy-architecture-skill",
    "server=ges_mcp_server",
    "tool=query_ges",
    "python3 scripts/run_deploy_architecture.py",
    "mcp-input.json",
    "最终必须返回脚本输出中的准确 htmlpath 和 url",
)
HEALTH_ALIAS_TO_KEY = {
    "正常": "ok",
    "ok": "ok",
    "healthy": "ok",
    "normal": "ok",
    "告警": "warn",
    "warn": "warn",
    "warning": "warn",
}

HEALTH_KEY_TO_DISPLAY = {
    "ok": "正常",
    "warn": "告警",
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
    "mysql": "db",
    "postgres": "db",
    "postgresql": "db",
    "oracle": "db",
    "mongodb": "db",
    "rds": "db",
    "middleware": "middleware",
    "中间件": "middleware",
    "redis": "middleware",
    "kafka": "middleware",
    "mq": "middleware",
    "rocketmq": "middleware",
    "rabbitmq": "middleware",
    "elasticsearch": "middleware",
    "compute": "compute",
    "计算": "compute",
    "计算资源": "compute",
    "node": "compute",
    "ec2": "compute",
    "ecs": "compute",
    "host": "compute",
    "storage": "storage",
    "存储": "storage",
    "efs": "storage",
    "esfs": "storage",
    "nfs": "storage",
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
    "storage": "存储",
    "alarm": "告警",
    "user": "用户",
    "domain": "域名上下文根",
}

RELATION_ALIAS_TO_KEY = {
    "access": "access",
    "访问": "access",
    "call": "call",
    "调用": "call",
    "calls": "calls",
    "lb": "lb",
    "loadbalance": "lb",
    "负载": "lb",
    "负载均衡": "lb",
    "host": "host",
    "承载": "host",
    "部署": "host",
    "monitor": "monitor",
    "监控": "monitor",
    "contains": "contains",
    "包含": "contains",
    "same_as": "same_as",
    "sameas": "same_as",
    "同一": "same_as",
    "等同": "same_as",
}

RELATION_KEY_TO_DISPLAY = {
    "access": "访问",
    "call": "调用",
    "calls": "调用",
    "lb": "负载均衡",
    "host": "承载",
    "monitor": "监控",
    "contains": "包含",
    "same_as": "同一资源",
}

RESOURCE_PROMPT_HINTS = [
    ("ec2", ["ec2"]),
    ("ecs", ["ecs"]),
    ("docker", ["docker", "容器"]),
    ("redis", ["redis"]),
    ("kafka", ["kafka"]),
    ("elasticsearch", ["elasticsearch", "es"]),
    ("mysql", ["mysql"]),
    ("postgres", ["postgres", "postgresql"]),
    ("oracle", ["oracle"]),
    ("rabbitmq", ["rabbitmq"]),
    ("rocketmq", ["rocketmq"]),
    ("esfs", ["esfs"]),
]

ENTITY_COLOR_MAP = {
    "用户": "#4db8ff",
    "域名上下文根": "#00e5ff",
    "API接口": "#ff8c33",
    "应用微服务": "#00d68f",
    "数据库": "#ffcc00",
    "中间件": "#9d6fff",
    "计算资源": "#7fa8cc",
    "存储": "#80d0ff",
    "告警": "#ff4040",
}

RELATION_COLOR_MAP = {
    "访问": "#4db8ff",
    "调用": "#00d68f",
    "负载均衡": "#9d6fff",
    "承载": "#7fa8cc",
    "监控": "#ff4040",
    "包含": "#4db8ff",
    "同一资源": "#9d6fff",
}

LAYER_COLOR_MAP = {
    "接入层": "#00e5ff",
    "入口层": "#00e5ff",
    "边缘层": "#00e5ff",
    "网关层": "#1a9fff",
    "API层": "#4db8ff",
    "应用层": "#00d68f",
    "服务层": "#00d68f",
    "业务层": "#00d68f",
    "中间件层": "#9d6fff",
    "缓存层": "#9d6fff",
    "消息层": "#9d6fff",
    "数据层": "#ffcc00",
    "数据库层": "#ffcc00",
    "存储层": "#80d0ff",
    "基础设施层": "#7fa8cc",
    "基础层": "#7fa8cc",
    "计算层": "#7fa8cc",
    "运维层": "#ff8c33",
    "监控层": "#ff8c33",
    "告警层": "#ff4040",
    "未分层": "#64748b",
}

LAYER_HINT_GROUPS = [
    ("接入层", ("接入", "入口", "访问", "边缘", "公网", "前端", "客户端", "域名", "用户", "access", "entry", "edge", "front")),
    ("网关层", ("网关", "gateway", "ingress", "代理", "路由", "api gateway")),
    ("应用层", ("应用", "服务", "业务", "service", "app", "logic")),
    ("中间件层", ("中间件", "消息", "缓存", "mq", "queue", "middleware", "cache", "redis", "kafka")),
    ("数据层", ("数据", "数据库", "存储", "db", "data", "storage", "mysql", "postgres", "oracle")),
    ("基础设施层", ("基础设施", "基础", "计算", "容器", "主机", "infra", "infrastructure", "compute", "host", "cluster")),
    ("运维层", ("运维", "监控", "可观测", "告警", "ops", "monitor", "alarm", "alert")),
]

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


def ensure_skill_cwd() -> None:
    cwd = Path.cwd().resolve()
    if cwd != SKILL_DIR:
        raise RuntimeError(f"Skill commands must run from {SKILL_DIR}, current cwd: {cwd}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deployment architecture from MCP JSON + natural language")
    parser.add_argument(
        "--input-json",
        default=str(DEFAULT_INPUT_JSON),
        help="Local JSON payload path; can be the original file returned by MCP, not necessarily runtime/mcp-input.json",
    )
    parser.add_argument("--prompt", default="", help="Natural-language request used to infer filters")
    parser.add_argument("--output", default="./out/dashboard.html", help="Output HTML file path")
    parser.add_argument("--open-output", action="store_true", help="Open the generated HTML with the local default app")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="HTML template file path")
    parser.add_argument("--title", default="Deploy Architecture Skill Demo", help="Dashboard title")
    return parser.parse_args()


def looks_like_skill_default_prompt(prompt: object) -> bool:
    text = str(prompt or "").strip()
    if not text:
        return False
    lowered = text.lower()
    hit_count = sum(1 for marker in SKILL_PROMPT_MARKERS if marker in lowered)
    return hit_count >= 2


def validate_runtime_prompt(prompt: object) -> str:
    text = str(prompt or "").strip()
    if not text:
        return ""
    if looks_like_skill_default_prompt(text):
        raise RuntimeError(
            "脚本参数 --prompt 收到了 skill 的说明文本，而不是用户本次原话。"
            "请把用户最新请求原样传给 --prompt，例如："
            '"把这个应用渲染成分层部署架构图"。'
        )
    return text


def read_json_file(path: Path) -> object:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def coerce_payload_object(payload: object) -> Dict:
    current = payload
    for _ in range(2):
        if isinstance(current, dict):
            return current
        if isinstance(current, str):
            text = current.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = next((part.strip() for part in parts if part.strip() and not part.strip().startswith("json")), "")
            if not text:
                break
            current = json.loads(text)
            continue
        break
    raise RuntimeError("MCP payload must be a JSON object or a JSON text string containing an object")


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


def normalize_project_value(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower() in INVALID_PROJECT_VALUES:
        return ""
    return text


def normalize_layer_value(value: object) -> str:
    return str(value or "").strip()


def layer_priority(label: object) -> int:
    text = normalize_layer_value(label)
    if not text:
        return 999
    lowered = text.lower()
    if text == "未分层":
        return 998
    for idx, (_, hints) in enumerate(LAYER_HINT_GROUPS):
        if any(hint in text or hint in lowered for hint in hints):
            return idx
    return 100


def build_node_reference_index(nodes: List[Dict], *, include_alarm_nodes: bool = True) -> Tuple[Dict[str, str], Dict[str, str]]:
    exact: Dict[str, str] = {}
    lowered: Dict[str, str] = {}

    for node in nodes:
        if not include_alarm_nodes and is_alarm_node_record(node):
            continue

        node_id = str(node.get("id") or node.get("entity_id") or "").strip()
        if not node_id:
            continue

        refs = [
            node_id,
            str(node.get("hrn") or "").strip(),
            str(node.get("resourceId") or node.get("resource_id") or "").strip(),
        ]
        for ref in refs:
            if not ref:
                continue
            exact.setdefault(ref, node_id)
            lowered.setdefault(ref.lower(), node_id)

    return exact, lowered


def resolve_node_reference(ref: object, exact_index: Dict[str, str], lowered_index: Dict[str, str]) -> str:
    text = str(ref or "").strip()
    if not text:
        return ""
    return exact_index.get(text) or lowered_index.get(text.lower(), "")


def resolve_project_id(raw: Dict, default_project: str = "UNKNOWN") -> str:
    candidates = [
        raw.get("project"),
        raw.get("project_id"),
        raw.get("app_id"),
        raw.get("appId"),
        raw.get("app_user"),
    ]
    for candidate in candidates:
        normalized = normalize_project_value(candidate)
        if normalized:
            return normalized
    fallback = normalize_project_value(default_project)
    return fallback or "UNKNOWN"


def normalize_node(raw: Dict, default_project: str = "UNKNOWN") -> Dict | None:
    node_id = str(raw.get("id") or raw.get("entity_id") or "").strip()
    if not node_id:
        return None

    resource_type_raw = (
        raw.get("resource_type")
        or raw.get("resourceType")
        or raw.get("resource_kind")
        or raw.get("resourceKind")
        or ""
    )
    resource_type_text = str(resource_type_raw or "").strip()
    resource_type_key = resource_type_text.lower()

    if resource_type_key == "alarm":
        node_type = "alarm"
    else:
        node_type = normalize_entity_key(
            str(
                raw.get("entity_type")
                or raw.get("entityType")
                or raw.get("resource_type")
                or raw.get("resourceType")
                or "unknown"
            )
        )
    project = resolve_project_id(raw, default_project=default_project)
    display_name = str(raw.get("label") or raw.get("name") or raw.get("resource_id") or node_id)
    hrn = str(raw.get("hrn") or "").strip()
    resource_id = str(raw.get("resource_id") or raw.get("resourceId") or node_id).strip() or node_id
    lifecycle_state = str(raw.get("lifecycle_state") or raw.get("lifecycleState") or "").strip()
    layer = normalize_layer_value(
        raw.get("type")
        or raw.get("layer")
        or raw.get("layer_type")
        or raw.get("layerType")
        or raw.get("tier")
    )
    if not layer:
        fallback_layer = key_to_entity_label(node_type)
        layer = fallback_layer if fallback_layer and fallback_layer != "未知" else (resource_type_text or "未分层")

    return {
        "id": node_id,
        "label": display_name,
        "type": node_type,
        "layer": layer or "未分层",
        "health": "",
        "healthText": "",
        "resourceType": resource_type_key,
        "resourceTypeRaw": resource_type_text,
        "resourceId": resource_id,
        "hrn": hrn,
        "lifecycleState": lifecycle_state,
        "project": project,
    }


def normalize_link(raw: Dict, exact_index: Dict[str, str], lowered_index: Dict[str, str]) -> Dict | None:
    source_raw = str(raw.get("startNode") or "").strip()
    target_raw = str(raw.get("endNode") or "").strip()
    source = resolve_node_reference(source_raw, exact_index, lowered_index)
    target = resolve_node_reference(target_raw, exact_index, lowered_index)
    if not source or not target:
        return None
    relation_type_raw = (
        raw.get("relation_type")
        or raw.get("relationType")
        or raw.get("type")
        or "unknown"
    )
    return {
        "source": source,
        "target": target,
        "type": normalize_relation_key(str(relation_type_raw)),
        "health": "",
        "healthText": "",
        "derivedFrom": str(raw.get("derived_from") or raw.get("derivedFrom") or "").strip(),
    }


def iter_data_entries(payload: Dict) -> List[Dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("MCP payload must be a JSON object")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("MCP payload must contain a 'data' object")

    datas = data.get("datas")
    if not isinstance(datas, list) or not datas:
        raise RuntimeError("MCP payload must contain a non-empty 'data.datas' array")

    entries: List[Dict] = []
    for index, item in enumerate(datas):
        if not isinstance(item, dict):
            raise RuntimeError(f"MCP payload data.datas[{index}] must be an object")
        if not isinstance(item.get("nodes"), list):
            raise RuntimeError(f"MCP payload data.datas[{index}].nodes must be an array")
        if not isinstance(item.get("relations"), list):
            raise RuntimeError(f"MCP payload data.datas[{index}].relations must be an array")
        entries.append(item)
    return entries


def normalize_payload(payload: Dict, default_project: str = "UNKNOWN") -> Dict[str, List[Dict]]:
    nodes_raw: List[Dict] = []
    links_raw: List[Dict] = []

    for entry in iter_data_entries(payload):
        raw_nodes = entry.get("nodes", [])
        if isinstance(raw_nodes, list):
            nodes_raw.extend(item for item in raw_nodes if isinstance(item, dict))

        raw_relations = entry.get("relations")
        if isinstance(raw_relations, list):
            links_raw.extend(item for item in raw_relations if isinstance(item, dict))

    nodes = [n for n in (normalize_node(item or {}, default_project=default_project) for item in nodes_raw) if n]
    exact_index, lowered_index = build_node_reference_index(nodes)
    links = [l for l in (normalize_link(item or {}, exact_index, lowered_index) for item in links_raw) if l]
    return {"nodes": nodes, "links": links}


def infer_keyword(prompt: str) -> str:
    explicit = re.search(r"(?:关键词|关键字|搜索|查找)\s*[:：]?\s*([^\n,，;；]+)", prompt, flags=re.I)
    if explicit:
        return explicit.group(1).strip()[:80]
    quoted = re.search(r"[\"“]([^\"”]{1,80})[\"”]", prompt)
    if quoted:
        return quoted.group(1).strip()[:80]
    return ""


def infer_filters_from_prompt(
    prompt: str,
    relation_types: Iterable[str] | None = None,
) -> Dict[str, str]:
    filters = {
        "project": "all",
        "entityType": "all",
        "relationType": "all",
        "health": "all",
        "keyword": "",
        "resourceType": "all",
        "expandNeighbors": "false",
    }
    text = str(prompt or "").strip()
    if not text:
        return filters

    low = text.lower()
    available_relation_types = {str(item).strip() for item in (relation_types or []) if str(item).strip()}

    relation_hints = [
        ("contains", ["包含", "归属", "contains"]),
        ("calls", ["调用", "call", "calls"]),
        ("same_as", ["同一", "等同", "same_as", "sameas"]),
        ("access", ["访问"]),
        ("call", ["调用"]),
        ("lb", ["负载", "lb"]),
        ("host", ["承载", "部署到", "运行在"]),
        ("monitor", ["监控"]),
    ]
    for key, hints in relation_hints:
        if any(h in low for h in hints):
            if key == "calls" and available_relation_types and key not in available_relation_types and "call" in available_relation_types:
                key = "call"
            filters["relationType"] = key
            break

    if re.search(r"告警|warn|warning", low):
        filters["health"] = "warn"
    elif re.search(r"正常|healthy|\bok\b", low):
        filters["health"] = "ok"

    if re.search(r"上下游|上游|下游|依赖|链路|调用链|upstream|downstream", low):
        filters["expandNeighbors"] = "true"

    for resource_type, hints in RESOURCE_PROMPT_HINTS:
        if any(hint in low for hint in hints):
            filters["resourceType"] = resource_type
            break

    filters["keyword"] = infer_keyword(text)
    return filters


def apply_filters(nodes: List[Dict], links: List[Dict], filters: Dict[str, str]) -> Tuple[List[Dict], List[Dict]]:
    keyword = filters.get("keyword", "").strip().lower()
    resource_filter_raw = str(filters.get("resourceType", "all") or "").strip().lower()
    resource_alias = {
        "docekr": "docker",
        "dockr": "docker",
        "es": "elasticsearch",
        "postgresql": "postgres",
    }
    resource_filters = []
    for part in re.split(r"[,\s，/]+", resource_filter_raw):
        token = part.strip()
        if not token or token == "all":
            continue
        token = resource_alias.get(token, token)
        if token not in resource_filters:
            resource_filters.append(token)
    expand_neighbors = str(filters.get("expandNeighbors", "")).strip().lower() in {"1", "true", "yes", "on"}
    alarm_node_ids, related_alarm_ids = build_alarm_index(nodes, links)

    def node_health_display(node: Dict) -> str:
        node_id = str(node.get("id") or node.get("entity_id") or "").strip()
        if node_id in alarm_node_ids or is_alarm_node_record(node):
            return ""
        return "告警" if related_alarm_ids.get(node_id) else "正常"

    def match_node(node: Dict) -> bool:
        if filters.get("project", "all") != "all" and node.get("project") != filters["project"]:
            return False
        if filters.get("entityType", "all") != "all" and node.get("type") != filters["entityType"]:
            return False
        health_filter = filters.get("health", "all")
        if health_filter != "all":
            if is_alarm_node_record(node):
                return False
            if health_to_key(node_health_display(node) or "正常") != health_filter:
                return False
        if resource_filters:
            node_resource = str(node.get("resourceType", "") or "").strip().lower()
            label = str(node.get("label", "") or "").lower()
            node_id = str(node.get("id", "") or "").lower()
            if not any(
                rt in node_resource or rt in label or rt in node_id
                for rt in resource_filters
            ):
                return False
        if keyword and keyword not in node.get("label", "").lower() and keyword not in node.get("id", "").lower():
            return False
        return True

    filtered_nodes = [node for node in nodes if match_node(node)]
    base_ids = {node["id"] for node in filtered_nodes}

    def link_matches_type(link: Dict) -> bool:
        if filters.get("relationType", "all") != "all" and link.get("type") != filters["relationType"]:
            return False
        return True

    if expand_neighbors and base_ids:
        candidate_links = [link for link in links if link_matches_type(link)]
        neighbor_ids = set(base_ids)
        for link in candidate_links:
            if link.get("source") in base_ids or link.get("target") in base_ids:
                neighbor_ids.add(link.get("source"))
                neighbor_ids.add(link.get("target"))
        expanded_nodes = [node for node in nodes if node.get("id") in neighbor_ids]
        expanded_links = [
            link for link in candidate_links
            if link.get("source") in neighbor_ids and link.get("target") in neighbor_ids
        ]
        if filters.get("health", "all") != "all":
            expanded_nodes = [node for node in expanded_nodes if not is_alarm_node_record(node)]
            expanded_ids = {node["id"] for node in expanded_nodes}
            expanded_links = [
                link for link in expanded_links
                if link.get("source") in expanded_ids and link.get("target") in expanded_ids
            ]
        return expanded_nodes, expanded_links

    node_ids = {node["id"] for node in filtered_nodes}
    filtered_links = [
        link
        for link in links
        if link.get("source") in node_ids
        and link.get("target") in node_ids
        and link_matches_type(link)
    ]
    return filtered_nodes, filtered_links


def build_summary(
    nodes: List[Dict],
    links: List[Dict],
    *,
    health_nodes: List[Dict] | None = None,
    health_links: List[Dict] | None = None,
) -> Dict:
    health_counter = {"ok": 0, "warn": 0, "err": 0}
    entity_counter: Dict[str, int] = {}
    projects = set()
    alarm_node_ids, related_alarm_ids = build_alarm_index(
        health_nodes if health_nodes is not None else nodes,
        health_links if health_links is not None else links,
    )
    visible_alarm_count = 0

    for node in nodes:
        node_id = str(node.get("id") or node.get("entity_id") or "").strip()
        project_id = normalize_project_value(node.get("project") or node.get("project_id") or "")
        if project_id and project_id not in {"global", "UNKNOWN"}:
            projects.add(project_id)
        et = key_to_entity_label(node.get("type") or node.get("entity_type") or "unknown")
        entity_counter[et] = entity_counter.get(et, 0) + 1
        if node_id in alarm_node_ids or is_alarm_node_record(node):
            visible_alarm_count += 1
            continue
        level = "告警" if related_alarm_ids.get(node_id) else "正常"
        h = health_to_key(level)
        health_counter[h] = health_counter.get(h, 0) + 1

    return {
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "projectCount": len(projects),
        "okCount": health_counter.get("ok", 0),
        "warnCount": health_counter.get("warn", 0),
        "errCount": health_counter.get("err", 0),
        "alarmCount": visible_alarm_count,
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


def build_layer_config(graph_data: Dict[str, List[Dict]]) -> List[Dict]:
    node_layers = {
        str(node.get("entity_id") or ""): normalize_layer_value(node.get("layer_type")) or "未分层"
        for node in graph_data.get("nodes", [])
        if node.get("entity_id")
    }
    all_layers = sorted(set(node_layers.values()), key=lambda label: (layer_priority(label), str(label)))
    if not all_layers:
        return [{"type": "未分层", "label": "未分层", "color": LAYER_COLOR_MAP["未分层"]}]

    outgoing: Dict[str, set[str]] = {layer: set() for layer in all_layers}
    indegree: Dict[str, int] = {layer: 0 for layer in all_layers}

    for relation in graph_data.get("relations", []):
        source_layer = node_layers.get(str(relation.get("source_entity_id") or ""), "")
        target_layer = node_layers.get(str(relation.get("target_entity_id") or ""), "")
        if not source_layer or not target_layer or source_layer == target_layer:
            continue
        if target_layer in outgoing[source_layer]:
            continue
        outgoing[source_layer].add(target_layer)
        indegree[target_layer] += 1

    ordered: List[str] = []
    queue = sorted(
        [layer for layer, degree in indegree.items() if degree == 0],
        key=lambda label: (layer_priority(label), str(label)),
    )
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for target in sorted(outgoing[current], key=lambda label: (layer_priority(label), str(label))):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
                queue.sort(key=lambda label: (layer_priority(label), str(label)))

    for layer in all_layers:
        if layer not in ordered:
            ordered.append(layer)

    return [
        {
            "type": layer,
            "label": layer,
            "color": pick_color(idx, LAYER_COLOR_MAP, layer),
        }
        for idx, layer in enumerate(ordered)
    ]


def is_alarm_node_record(node: Dict) -> bool:
    resource_type = str(
        node.get("resourceTypeRaw")
        or node.get("resourceType")
        or node.get("resource_type")
        or ""
    ).strip().lower()
    if resource_type == "alarm":
        return True

    node_type = str(node.get("type") or node.get("entity_type") or "").strip()
    if not node_type:
        return False
    if node_type.lower() == "alarm":
        return True
    return key_to_entity_label(node_type) == "告警" or node_type == "告警"


def build_alarm_index(nodes: List[Dict], links: List[Dict]) -> Tuple[set[str], Dict[str, set[str]]]:
    node_ids = {str(node.get("id") or node.get("entity_id") or "").strip() for node in nodes}
    alarm_node_ids = {
        str(node.get("id") or node.get("entity_id") or "").strip()
        for node in nodes
        if is_alarm_node_record(node)
    }

    related_alarm_ids: Dict[str, set[str]] = {node_id: set() for node_id in node_ids if node_id}
    for link in links:
        source = str(link.get("source") or link.get("source_entity_id") or "").strip()
        target = str(link.get("target") or link.get("target_entity_id") or "").strip()
        if not source or not target:
            continue
        if source in alarm_node_ids and target not in alarm_node_ids:
            related_alarm_ids.setdefault(target, set()).add(source)
        elif target in alarm_node_ids and source not in alarm_node_ids:
            related_alarm_ids.setdefault(source, set()).add(target)

    return alarm_node_ids, related_alarm_ids


def node_health_fields(node: Dict, alarm_node_ids: set[str], related_alarm_ids: Dict[str, set[str]]) -> Tuple[str, str, int, bool]:
    node_id = str(node.get("id") or node.get("entity_id") or "").strip()
    is_alarm_node = node_id in alarm_node_ids or is_alarm_node_record(node)
    alarm_count = len(related_alarm_ids.get(node_id, set()))
    if is_alarm_node:
        return "", "", alarm_count, True
    health_display = "告警" if alarm_count > 0 else "正常"
    return health_display, health_display, alarm_count, False


def to_graph_data(nodes: List[Dict], links: List[Dict]) -> Dict[str, List[Dict]]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alarm_node_ids, related_alarm_ids = build_alarm_index(nodes, links)

    graph_nodes: List[Dict] = []
    for node in nodes:
        node_id = node["id"]
        health_status, health_level, alarm_count, is_alarm_node = node_health_fields(
            node,
            alarm_node_ids,
            related_alarm_ids,
        )
        graph_nodes.append(
            {
                "entity_id": node_id,
                "entity_name": node.get("label", node_id),
                "entity_type": key_to_entity_label(node.get("type", "unknown")),
                "layer_type": node.get("layer") or key_to_entity_label(node.get("type", "unknown")) or "未分层",
                "project_id": node.get("project", "UNKNOWN"),
                "health_status": health_status,
                "health_level": health_level,
                "health_text": health_status,
                "is_alarm_node": is_alarm_node,
                "alarm_count": alarm_count,
                "resource_id": node.get("resourceId") or node_id,
                "resource_type": node.get("resourceTypeRaw") or node.get("resourceType") or "",
                "hrn": node.get("hrn") or "",
                "lifecycle_state": node.get("lifecycleState") or "",
                "created_at": now,
                "updated_at": now,
            }
        )

    graph_relations: List[Dict] = []
    for idx, link in enumerate(links, start=1):
        graph_relations.append(
            {
                "relation_id": f"R-{idx:05d}",
                "relation_type": key_to_relation_label(link.get("type", "unknown")),
                "source_entity_id": link.get("source"),
                "target_entity_id": link.get("target"),
                "health_status": "",
                "health_level": "",
                "health_text": "",
                "derived_from": link.get("derivedFrom", ""),
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
            if n.get("project_id") and n.get("project_id") not in {"global", "UNKNOWN"}
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
        "存储",
        "告警",
    ]
    known_relation_order = ["访问", "调用", "包含", "同一资源", "负载均衡", "承载", "监控"]

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
        "layerTypes": build_layer_config(graph_data),
        "layout": DEFAULT_LAYOUT,
        "healthStates": ["正常", "告警"],
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
        "resourceType": filters.get("resourceType", "all"),
        "expandNeighbors": filters.get("expandNeighbors", "false"),
    }


def render_dashboard(
    template_path: Path,
    title: str,
    graph_data: Dict,
    app_config: Dict,
    skill_state: Dict,
    output_path: Path,
) -> None:
    template = template_path.read_text(encoding="utf-8")
    rendered = template.replace("__DASHBOARD_TITLE__", title)
    rendered = rendered.replace("__GRAPH_DATA_JSON__", json.dumps(graph_data, ensure_ascii=False))
    rendered = rendered.replace("__APP_CONFIG_JSON__", json.dumps(app_config, ensure_ascii=False))
    rendered = rendered.replace("__SKILL_STATE_JSON__", json.dumps(skill_state, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def open_output_file(path: Path) -> tuple[bool, str]:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def derive_app_id(nodes: List[Dict]) -> str:
    projects = sorted(
        {
            project
            for node in nodes
            if (project := normalize_project_value(node.get("project")))
            and project not in {"global", "UNKNOWN"}
        }
    )
    if len(projects) == 1:
        return projects[0]
    return ""


def load_source_data(args: argparse.Namespace) -> Tuple[Dict[str, List[Dict]], BuildContext]:
    ensure_skill_cwd()
    input_path = Path(str(getattr(args, "input_json", "") or DEFAULT_INPUT_JSON)).expanduser().resolve()
    if not input_path.exists():
        raise RuntimeError(f"MCP input JSON not found: {input_path}")

    try:
        payload = coerce_payload_object(read_json_file(input_path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MCP input JSON is invalid: {exc}") from exc

    normalized = normalize_payload(payload, default_project="UNKNOWN")
    if not normalized["nodes"] and not normalized["links"]:
        raise RuntimeError("MCP returned no graph data (nodes=0, relations=0); report this directly to the user and do not fabricate data")
    return normalized, BuildContext(
        source=f"input:{input_path}",
        raw_node_count=len(normalized["nodes"]),
        raw_link_count=len(normalized["links"]),
    )


def main() -> int:
    args = parse_args()

    try:
        args.prompt = validate_runtime_prompt(args.prompt)
        normalized, ctx = load_source_data(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    filters = infer_filters_from_prompt(
        args.prompt,
        relation_types=[link.get("type", "") for link in normalized["links"]],
    )
    filtered_nodes, filtered_links = apply_filters(normalized["nodes"], normalized["links"], filters)
    summary = build_summary(
        filtered_nodes,
        filtered_links,
        health_nodes=normalized["nodes"],
        health_links=normalized["links"],
    )
    app_id = derive_app_id(normalized["nodes"])

    graph_data = to_graph_data(normalized["nodes"], normalized["links"])
    app_config = build_app_config(graph_data)
    ui_filters = to_ui_filters(filters)

    meta = {
        "source": ctx.source,
        "rawNodeCount": ctx.raw_node_count,
        "rawLinkCount": ctx.raw_link_count,
        "appId": app_id,
    }

    skill_state = {
        "prompt": args.prompt,
        "filters": ui_filters,
        "summary": summary,
        "meta": meta,
    }

    meta_payload = {
        "title": args.title,
        "prompt": args.prompt,
        "filters": filters,
        "uiFilters": ui_filters,
        "summary": summary,
        "appConfig": app_config,
        "skillState": skill_state,
        "meta": meta,
        "filtered": {
            "nodeCount": len(filtered_nodes),
            "linkCount": len(filtered_links),
        },
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    }

    output_path = Path(args.output).expanduser().resolve()
    template_path = Path(args.template).expanduser().resolve()

    try:
        render_dashboard(template_path, args.title, graph_data, app_config, skill_state, output_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] render failed: {exc}", file=sys.stderr)
        return 3

    meta_path = output_path.parent / f"{output_path.stem}.meta.json"
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    opened = False
    open_error = ""
    if args.open_output:
        opened, open_error = open_output_file(output_path)

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output_path),
                "htmlPath": str(output_path),
                "meta": str(meta_path),
                "filters": filters,
                "uiFilters": ui_filters,
                "summary": summary,
                "opened": opened,
                "openError": open_error,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
