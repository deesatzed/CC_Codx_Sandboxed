"""OpenAI Responses API helpers for the Codex path on the hybrid router."""
from __future__ import annotations

import json
import time
from typing import Any

_STUB = (
    "You are a local coding agent on this Mac. Prefer small file reads. "
    "Do not claim to be GPT or Opus. Do not call Hugging Face."
)


def compress_responses_for_local(body: dict[str, Any], *, local_model: str) -> dict[str, Any]:
    out = dict(body)
    out["model"] = local_model
    inst = body.get("instructions")
    if isinstance(inst, str) and inst:
        out["instructions"] = _STUB
    elif inst:
        out["instructions"] = _STUB
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
    text = extract_output_text(resp)
    chunks: list[str] = []

    def event(name: str, data: dict[str, Any]) -> None:
        chunks.append(f"event: {name}\ndata: {json.dumps(data)}\n\n")

    event("response.created", {"type": "response.created", "response": {**resp, "status": "in_progress", "output": []}})
    event(
        "response.output_text.delta",
        {"type": "response.output_text.delta", "delta": text},
    )
    event("response.completed", {"type": "response.completed", "response": resp})
    return "".join(chunks)
