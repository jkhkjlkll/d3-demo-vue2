#!/usr/bin/env python3
"""Export the normalized ops graph into Mermaid syntax (graph LR/TB).

This reads the live session meta JSON (dashboard.meta.json) and emits a .mmd file
so agents can render or embed Mermaid diagrams elsewhere.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export ops graph to Mermaid .mmd")
    parser.add_argument("--meta", required=True, help="Path to dashboard.meta.json")
    parser.add_argument("--output", default="", help="Output .mmd file path")
    parser.add_argument("--direction", default="LR", choices=["LR", "TB", "RL", "BT"], help="Mermaid graph direction")
    parser.add_argument("--max-nodes", type=int, default=400, help="Max nodes to emit")
    parser.add_argument("--max-edges", type=int, default=800, help="Max edges to emit")
    parser.add_argument("--label-max", type=int, default=48, help="Max node label length")
    parser.add_argument(
        "--with-edge-labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include relation labels on edges",
    )
    return parser.parse_args()


def load_meta(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_label(text: str, limit: int) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1] + "…"
    return cleaned.replace('"', "'")


def normalize_graph(meta: Dict) -> Tuple[List[Dict], List[Dict]]:
    dataset = meta.get("dataset") or {}
    nodes = dataset.get("nodes") or []
    links = dataset.get("links") or []
    if nodes and links:
        return nodes, links

    graph = meta.get("graphData") or {}
    graph_nodes = []
    for node in graph.get("nodes", []) or []:
        graph_nodes.append(
            {
                "id": node.get("entity_id") or node.get("id") or "",
                "label": node.get("entity_name") or node.get("label") or "",
                "type": node.get("entity_type") or node.get("type") or "",
            }
        )
    graph_links = []
    for link in graph.get("relations", []) or []:
        graph_links.append(
            {
                "source": link.get("source_entity_id") or link.get("source") or "",
                "target": link.get("target_entity_id") or link.get("target") or "",
                "type": link.get("relation_type") or link.get("type") or "",
            }
        )
    return graph_nodes, graph_links


def pick_nodes(nodes: Iterable[Dict], max_nodes: int) -> List[Dict]:
    ordered = sorted((n for n in nodes if n.get("id")), key=lambda n: str(n.get("id")))
    if max_nodes <= 0:
        return ordered
    return ordered[:max_nodes]


def pick_edges(links: Iterable[Dict], allowed_ids: set, max_edges: int) -> List[Dict]:
    ordered = sorted(
        (l for l in links if l.get("source") in allowed_ids and l.get("target") in allowed_ids),
        key=lambda l: (str(l.get("source")), str(l.get("target")), str(l.get("type"))),
    )
    if max_edges <= 0:
        return ordered
    return ordered[:max_edges]


def build_mermaid(nodes: List[Dict], links: List[Dict], direction: str, label_max: int, edge_labels: bool) -> str:
    node_ids = [str(n.get("id")) for n in nodes]
    alias_map = {node_id: f"N{idx+1}" for idx, node_id in enumerate(node_ids)}

    lines = [f"graph {direction}"]
    for node in nodes:
        node_id = str(node.get("id"))
        alias = alias_map[node_id]
        label = sanitize_label(node.get("label") or node_id, label_max)
        ntype = sanitize_label(node.get("type") or "", label_max)
        if ntype:
            lines.append(f'  {alias}["{label} ({ntype})"]')
        else:
            lines.append(f'  {alias}["{label}"]')

    for link in links:
        src = alias_map.get(str(link.get("source")))
        tgt = alias_map.get(str(link.get("target")))
        if not src or not tgt:
            continue
        if edge_labels:
            ltype = sanitize_label(link.get("type") or "", label_max)
            if ltype:
                lines.append(f'  {src} -- "{ltype}" --> {tgt}')
            else:
                lines.append(f"  {src} --> {tgt}")
        else:
            lines.append(f"  {src} --> {tgt}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    meta_path = Path(args.meta).expanduser().resolve()
    if not meta_path.exists():
        raise SystemExit(f"[ERROR] meta file not found: {meta_path}")

    meta = load_meta(meta_path)
    nodes, links = normalize_graph(meta)
    picked_nodes = pick_nodes(nodes, args.max_nodes)
    allowed_ids = {str(n.get("id")) for n in picked_nodes}
    picked_links = pick_edges(links, allowed_ids, args.max_edges)

    mermaid = build_mermaid(
        picked_nodes,
        picked_links,
        direction=args.direction,
        label_max=args.label_max,
        edge_labels=bool(args.with_edge_labels),
    )

    output = args.output.strip()
    if not output:
        output = str(meta_path.with_suffix(".mmd"))
    output_path = Path(output).expanduser().resolve()
    output_path.write_text(mermaid, encoding="utf-8")

    result = {
        "ok": True,
        "output": str(output_path),
        "nodeCount": len(picked_nodes),
        "edgeCount": len(picked_links),
        "truncatedNodes": len(nodes) > len(picked_nodes),
        "truncatedEdges": len(links) > len(picked_links),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
