"""Lossy shrink of an Anthropic /v1/messages body for the local 27B only."""
from __future__ import annotations

from typing import Any

_STUB = (
    "You are a local coding agent on this Mac. Use Anthropic tool_use blocks "
    "(name + input) when you need files or a shell. Prefer small Reads. "
    "Do not claim to be Opus, Sonnet, or Claude. Do not call Hugging Face. "
    "If a tool is listed, you may call it by that exact name."
)
_TOOL_RESULT_MAX = 4000


def compress_for_local(body: dict[str, Any], *, local_model: str) -> dict[str, Any]:
    out = dict(body)
    out["model"] = local_model
    out["system"] = _STUB
    if isinstance(body.get("tools"), list):
        out["tools"] = [_slim_tool(t) for t in body["tools"] if isinstance(t, dict)]
    if isinstance(body.get("messages"), list):
        out["messages"] = [_slim_message(m) for m in body["messages"] if isinstance(m, dict)]
    return out


def _slim_tool(tool: dict[str, Any]) -> dict[str, Any]:
    schema = tool.get("input_schema") if isinstance(tool.get("input_schema"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    slim_props = {k: {"type": (v or {}).get("type", "string")} for k, v in list(props.items())[:12] if isinstance(v, dict)}
    desc = str(tool.get("description") or "")
    return {
        "name": tool.get("name"),
        "description": desc[:240],
        "input_schema": {
            "type": "object",
            "properties": slim_props,
            "required": required,
        },
    }


def _slim_message(msg: dict[str, Any]) -> dict[str, Any]:
    content = msg.get("content")
    if isinstance(content, list):
        return {**msg, "content": [_slim_block(b) for b in content]}
    if isinstance(content, str) and len(content) > _TOOL_RESULT_MAX:
        return {**msg, "content": _truncate(content)}
    return dict(msg)


def _slim_block(block: Any) -> Any:
    if not isinstance(block, dict):
        return block
    if block.get("type") == "tool_result":
        raw = block.get("content")
        text = raw if isinstance(raw, str) else str(raw)
        if len(text) > _TOOL_RESULT_MAX:
            return {**block, "content": _truncate(text)}
    return block


def _truncate(text: str) -> str:
    keep = _TOOL_RESULT_MAX // 2
    return text[:keep] + "\n\n[truncated tool result]\n\n" + text[-keep:]
