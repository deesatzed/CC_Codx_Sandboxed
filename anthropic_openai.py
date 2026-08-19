"""Anthropic Messages bodies ↔ OpenAI Chat Completions (tools included)."""
from __future__ import annotations

import json
from typing import Any


def flatten_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content) if content is not None else ""


def to_openai_chat(body: dict[str, Any], *, model: str) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    system = body.get("system", "")
    if system:
        messages.append({"role": "system", "content": flatten_content(system)})
    for msg in body.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        messages.extend(_openai_from_anthropic_message(msg))
    out: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": int(body.get("max_tokens") or 4096),
        "stream": False,
    }
    if body.get("temperature") is not None:
        out["temperature"] = body["temperature"]
    tools = body.get("tools")
    if isinstance(tools, list) and tools:
        out["tools"] = [_openai_tool(t) for t in tools if isinstance(t, dict) and t.get("name")]
    return out


def openai_chat_to_anthropic(data: dict[str, Any], *, model: str) -> dict[str, Any]:
    choice = (data.get("choices") or [{}])[0] or {}
    message = choice.get("message") or {}
    content_blocks: list[dict[str, Any]] = []
    text = message.get("content")
    if isinstance(text, str) and text:
        content_blocks.append({"type": "text", "text": text})
    for call in message.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            parsed = {"_raw": raw_args}
        if not isinstance(parsed, dict):
            parsed = {"_raw": parsed}
        content_blocks.append(
            {
                "type": "tool_use",
                "id": str(call.get("id") or "tool_local"),
                "name": fn.get("name") or "unknown",
                "input": parsed,
            }
        )
    finish = choice.get("finish_reason") or "stop"
    stop_reason = "tool_use" if finish == "tool_calls" else ("end_turn" if finish == "stop" else finish)
    usage = data.get("usage") or {}
    return {
        "id": data.get("id") or "msg_local",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks or [{"type": "text", "text": ""}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens") or 0,
            "output_tokens": usage.get("completion_tokens") or 0,
        },
    }


def anthropic_to_sse(message: dict[str, Any]) -> str:
    """Replay a complete Anthropic message as SSE (Claude Code stream=true)."""
    chunks: list[str] = []

    def event(name: str, data: dict[str, Any]) -> None:
        chunks.append(f"event: {name}\ndata: {json.dumps(data)}\n\n")

    event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": message.get("id") or "msg_local",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": message.get("model"),
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": (message.get("usage") or {}).get("input_tokens") or 0, "output_tokens": 0},
            },
        },
    )
    for i, block in enumerate(message.get("content") or []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            event(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": i,
                    "content_block": {"type": "text", "text": ""},
                },
            )
            event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": i,
                    "delta": {"type": "text_delta", "text": block.get("text") or ""},
                },
            )
            event("content_block_stop", {"type": "content_block_stop", "index": i})
        elif block.get("type") == "tool_use":
            event(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": i,
                    "content_block": {
                        "type": "tool_use",
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": {},
                    },
                },
            )
            event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": i,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps(block.get("input") or {}),
                    },
                },
            )
            event("content_block_stop", {"type": "content_block_stop", "index": i})
    event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {
                "stop_reason": message.get("stop_reason") or "end_turn",
                "stop_sequence": None,
            },
            "usage": {"output_tokens": (message.get("usage") or {}).get("output_tokens") or 0},
        },
    )
    event("message_stop", {"type": "message_stop"})
    return "".join(chunks)


def _openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    schema = tool.get("input_schema") if isinstance(tool.get("input_schema"), dict) else {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description") or "",
            "parameters": schema,
        },
    }


def _openai_from_anthropic_message(msg: dict[str, Any]) -> list[dict[str, Any]]:
    role = msg.get("role") or "user"
    content = msg.get("content")
    if isinstance(content, str):
        return [{"role": role, "content": content}]
    if not isinstance(content, list):
        return [{"role": role, "content": flatten_content(content)}]

    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text") or "")
        elif btype == "tool_use":
            tool_calls.append(
                {
                    "id": str(block.get("id") or "tool_local"),
                    "type": "function",
                    "function": {
                        "name": block.get("name") or "unknown",
                        "arguments": json.dumps(block.get("input") or {}),
                    },
                }
            )
        elif btype == "tool_result":
            raw = block.get("content")
            text = raw if isinstance(raw, str) else json.dumps(raw)
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": str(block.get("tool_use_id") or ""),
                    "content": text,
                }
            )

    out: list[dict[str, Any]] = []
    if tool_calls:
        item: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(text_parts) or None,
            "tool_calls": tool_calls,
        }
        out.append(item)
    elif text_parts:
        out.append({"role": role, "content": "".join(text_parts)})
    out.extend(tool_results)
    return out or [{"role": role, "content": ""}]
