"""Append-only hop receipts and real-refusal corpus. No mocked hops."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_ROOT_DEFAULT = Path(__file__).resolve().parent
_MAX_EXCERPT = 500


def consume_force_local(root: Path | None = None) -> bool:
    flag = (root or _ROOT_DEFAULT) / ".force-local"
    if not flag.is_file():
        return False
    try:
        flag.unlink()
    except FileNotFoundError:
        return False
    return True


def write_hop(
    root: Path | None = None,
    *,
    via: str,
    reason: str,
    route: str,
    or_status: int | None = None,
    err: str | None = None,
    usage: dict[str, Any] | None = None,
    or_excerpt: str = "",
    local_excerpt: str = "",
    graph_injected: bool = False,
    host: str = "router",
) -> dict[str, Any]:
    base = root or _ROOT_DEFAULT
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": host,
        "route": route,
        "via": via,
        "reason": reason,
        "or_status": or_status,
        "err": err,
        "usage": usage or {},
        "graph_injected": bool(graph_injected),
        "or_excerpt": _excerpt(or_excerpt),
        "local_excerpt": _excerpt(local_excerpt),
    }
    _append(base / "receipts" / "hops.jsonl", rec)
    return rec


def write_refusal_if_real(root: Path | None, hop: dict[str, Any]) -> None:
    if hop.get("reason") not in {"R1", "R2", "R3", "R4"}:
        return
    if hop.get("via") != "local":
        return
    rec = {
        "ts": hop.get("ts"),
        "reason": hop.get("reason"),
        "or_status": hop.get("or_status"),
        "or_excerpt": hop.get("or_excerpt") or "",
        "local_excerpt": hop.get("local_excerpt") or "",
        "route": hop.get("route"),
    }
    _append((root or _ROOT_DEFAULT) / "receipts" / "refusals.jsonl", rec)


def latest_hop(root: Path | None = None) -> dict[str, Any] | None:
    path = (root or _ROOT_DEFAULT) / "receipts" / "hops.jsonl"
    if not path.is_file():
        return None
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        rec = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return rec if isinstance(rec, dict) else None


def _excerpt(text: str) -> str:
    raw = (text or "").replace("\x00", "")
    for needle in ("sk-or-v1-", "Bearer ", "OPENROUTER_API_KEY"):
        if needle.lower() in raw.lower() or needle in raw:
            raw = "[redacted excerpt]"
            break
    return raw[:_MAX_EXCERPT]


def _append(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
