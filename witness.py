"""Append-only witness log for Claude + Codex in this Safehouse."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_ROOT_DEFAULT = Path(__file__).resolve().parent


def append_witness(
    root: Path | None = None,
    *,
    host: str,
    event: str,
    tool: str = "",
    path: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": host,
        "event": event,
        "tool": tool,
        "path": path[:500],
    }
    if extra:
        rec["extra"] = extra
    dest = (root or _ROOT_DEFAULT) / "witness.jsonl"
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def hook_from_stdin(host: str, root: Path | None = None) -> None:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    tool = ""
    path = ""
    payload: dict[str, Any] | None = None
    if raw.strip():
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict):
        tool = str(payload.get("tool_name") or payload.get("tool") or "")
        inp = payload.get("tool_input") or payload.get("input") or {}
        if isinstance(inp, dict):
            path = str(inp.get("command") or inp.get("file_path") or inp.get("path") or inp.get("pattern") or "")
        elif isinstance(inp, str):
            path = inp
    append_witness(root, host=host, event="tool", tool=tool, path=path)


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    hook_from_stdin(host)
