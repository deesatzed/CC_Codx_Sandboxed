"""OpenAI Responses API helpers for the Codex path on the hybrid router."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from graph_context import compact_subgraph, last_user_text

_ROOT = Path(__file__).resolve().parent

_STUB = (
    "You are a local coding agent on this Mac. Prefer small file reads. "
    "Do not claim to be GPT or Opus. Do not call Hugging Face."
)


def compress_responses_for_local(body: dict[str, Any], *, local_model: str) -> dict[str, Any]:
    out = dict(body)
    out["model"] = local_model
    graph = compact_subgraph(_ROOT / "graphify-out" / "graph.json", last_user_text(body))
    inst = _STUB + (("\n\n" + graph) if graph else "")
    if body.get("instructions"):
        out["instructions"] = inst
    inp = body.get("input")
    if isinstance(inp, str) and len(inp) > 8000:
        out["input"] = inp[:4000] + "\n\n[truncated]\n\n" + inp[-4000:]
    return out


def extract_output_text(resp: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in resp.get("output") or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content") or []:
            if isinstance(block, dict) and block.get("type") in {"output_text", "text"}:
                parts.append(str(block.get("text") or ""))
        if item.get("type") == "message" and isinstance(item.get("content"), str):
            parts.append(item["content"])
    return "".join(parts)


def wrap_chat_as_response(chat: dict[str, Any], *, model: str) -> dict[str, Any]:
    choice = (chat.get("choices") or [{}])[0] or {}
    message = choice.get("message") or {}
    text = message.get("content") if isinstance(message.get("content"), str) else ""
    rid = chat.get("id") or f"resp_{int(time.time())}"
    return {
        "id": rid,
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": "msg_local",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text or ""}],
            }
        ],
        "usage": chat.get("usage") or {},
    }


def responses_to_sse(resp: dict[str, Any]) -> str:
    """Replay a completed Responses object as the event sequence Codex expects.

    Codex errors with 'OutputTextDelta without active item' if we emit
    output_text.delta before output_item.added.
    """
    chunks: list[str] = []

    def event(name: str, data: dict[str, Any]) -> None:
        chunks.append(f"event: {name}\ndata: {json.dumps(data)}\n\n")

    skeleton = {**resp, "status": "in_progress", "output": []}
    event("response.created", {"type": "response.created", "response": skeleton})
    event("response.in_progress", {"type": "response.in_progress", "response": skeleton})

    items = [i for i in (resp.get("output") or []) if isinstance(i, dict)]
    if not items:
        text = extract_output_text(resp)
        items = [
            {
                "id": "msg_local",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }
        ]

    for output_index, item in enumerate(items):
        event(
            "response.output_item.added",
            {
                "type": "response.output_item.added",
                "output_index": output_index,
                "item": {**item, "status": item.get("status") or "in_progress"},
            },
        )
        if item.get("type") == "function_call":
            args = item.get("arguments") or ""
            event(
                "response.function_call_arguments.delta",
                {
                    "type": "response.function_call_arguments.delta",
                    "output_index": output_index,
                    "delta": args,
                },
            )
            event(
                "response.function_call_arguments.done",
                {
                    "type": "response.function_call_arguments.done",
                    "output_index": output_index,
                    "arguments": args,
                },
            )

        content = item.get("content")
        if isinstance(content, list):
            for content_index, part in enumerate(content):
                if not isinstance(part, dict):
                    continue
                start_part = dict(part)
                if start_part.get("type") in {"output_text", "text"}:
                    start_part["text"] = ""
                event(
                    "response.content_part.added",
                    {
                        "type": "response.content_part.added",
                        "output_index": output_index,
                        "content_index": content_index,
                        "part": start_part,
                    },
                )
                text = part.get("text") or ""
                if part.get("type") in {"output_text", "text"} and text:
                    event(
                        "response.output_text.delta",
                        {
                            "type": "response.output_text.delta",
                            "output_index": output_index,
                            "content_index": content_index,
                            "delta": text,
                        },
                    )
                    event(
                        "response.output_text.done",
                        {
                            "type": "response.output_text.done",
                            "output_index": output_index,
                            "content_index": content_index,
                            "text": text,
                        },
                    )
                event(
                    "response.content_part.done",
                    {
                        "type": "response.content_part.done",
                        "output_index": output_index,
                        "content_index": content_index,
                        "part": part,
                    },
                )
        event(
            "response.output_item.done",
            {
                "type": "response.output_item.done",
                "output_index": output_index,
                "item": item,
            },
        )

    event("response.completed", {"type": "response.completed", "response": resp})
    return "".join(chunks)
