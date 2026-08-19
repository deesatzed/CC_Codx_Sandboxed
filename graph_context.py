"""Compact subgraph from Graphify graph.json. Empty string if missing — never fake."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compact_subgraph(graph_path: Path, query: str, *, max_nodes: int = 24) -> str:
    if not graph_path.is_file():
        return ""
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    nodes, edges = _nodes_edges(data)
    if not nodes:
        return ""
    q = (query or "").lower()
    tokens = [t for t in _split(q) if len(t) > 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    for node in nodes:
        blob = " ".join(
            str(node.get(k) or "")
            for k in ("id", "label", "name", "source_file", "file")
        ).lower()
        hits = sum(1 for t in tokens if t in blob) if tokens else 0
        scored.append((hits, node))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id") or "")))
    picked = [n for s, n in scored if s > 0][:max_nodes]
    if not picked:
        picked = [n for _, n in scored[: min(8, max_nodes)]]
    ids = {_nid(n) for n in picked}
    # one hop of neighbors
    extra: list[dict[str, Any]] = []
    for edge in edges:
        src, dst = _eid(edge, "source"), _eid(edge, "target")
        if src in ids or dst in ids:
            extra.extend([src, dst])
    by_id = {_nid(n): n for n in nodes}
    for eid in extra:
        if eid and eid not in ids and eid in by_id:
            picked.append(by_id[eid])
            ids.add(eid)
            if len(picked) >= max_nodes:
                break
    rels = []
    for edge in edges:
        src, dst = _eid(edge, "source"), _eid(edge, "target")
        if src in ids and dst in ids:
            rel = edge.get("rel") or edge.get("type") or edge.get("relation") or "related"
            conf = edge.get("confidence") or edge.get("tag") or ""
            rels.append(f"{src} --{rel}--> {dst}" + (f" [{conf}]" if conf else ""))
            if len(rels) >= 40:
                break
    lines = ["GRAPH (compact, from graphify-out/graph.json):"]
    for node in picked[:max_nodes]:
        src = node.get("source_file") or node.get("file") or ""
        lines.append(f"- { _nid(node) }" + (f"  {src}" if src else ""))
    if rels:
        lines.append("EDGES:")
        lines.extend(rels[:40])
    text = "\n".join(lines)
    return text[:2400]


def last_user_text(body: dict[str, Any]) -> str:
    msgs = body.get("messages")
    if isinstance(msgs, list):
        for msg in reversed(msgs):
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "user":
                return _content_text(msg.get("content"))
    inp = body.get("input")
    if isinstance(inp, str):
        return inp[-2000:]
    if isinstance(inp, list):
        for item in reversed(inp):
            if isinstance(item, dict) and item.get("role") == "user":
                return _content_text(item.get("content") or item.get("text"))
    inst = body.get("instructions")
    if isinstance(inst, str):
        return inst[-500:]
    return ""


def _nodes_edges(data: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if isinstance(data, dict):
        nodes = data.get("nodes")
        edges = data.get("edges") or data.get("links")
        nested = data.get("graph")
        if isinstance(nested, dict):
            nodes = nodes or nested.get("nodes")
            edges = edges or nested.get("edges") or nested.get("links")
        return (
            [n for n in (nodes or []) if isinstance(n, dict)],
            [e for e in (edges or []) if isinstance(e, dict)],
        )
    return [], []


def _nid(node: dict[str, Any]) -> str:
    return str(node.get("id") or node.get("label") or node.get("name") or "?")


def _eid(edge: dict[str, Any], key: str) -> str:
    val = edge.get(key) or edge.get("from" if key == "source" else "to")
    if isinstance(val, dict):
        return str(val.get("id") or "")
    return str(val or "")


def _split(q: str) -> list[str]:
    out: list[str] = []
    cur = []
    for ch in q:
        if ch.isalnum() or ch in {"_", "-"}:
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur).lower())
                cur = []
    if cur:
        out.append("".join(cur).lower())
    return out


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content or "")
