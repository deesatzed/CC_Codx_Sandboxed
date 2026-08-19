#!/usr/bin/env python3
"""Optional Anthropic Messages → OpenAI Chat Completions proxy.

Default path does not use this: mlx_vlm.server already has POST /v1/messages.
Use only if Claude Code cannot speak that dialect.

  Claude Code → this process (:4000) → mlx_vlm.server (:8080)
"""
from __future__ import annotations

import json
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

MLX_URL = os.environ.get("MLX_URL", os.environ.get("LLAMAFILE_URL", "http://127.0.0.1:8080"))
PORT = int(os.environ.get("PROXY_PORT", "4000"))

app = FastAPI()


def flatten_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


def to_openai_messages(body: dict) -> list:
    messages = []
    system = body.get("system", "")
    if system:
        messages.append({"role": "system", "content": flatten_content(system)})
    for msg in body.get("messages", []):
        messages.append(
            {
                "role": msg["role"],
                "content": flatten_content(msg.get("content", "")),
            }
        )
    return messages


def openai_resp_to_anthropic(data: dict, model: str) -> dict:
    choice = data.get("choices", [{}])[0]
    text = choice.get("message", {}).get("content", "")
    usage = data.get("usage", {})
    return {
        "id": data.get("id", "msg_local"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


async def stream_anthropic(openai_body: dict, model: str):
    def event(name: str, data: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(data)}\n\n"

    yield event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": "msg_local",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        },
    )
    yield event(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
    )
    yield event("ping", {"type": "ping"})

    output_tokens = 0
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST",
            f"{MLX_URL}/v1/chat/completions",
            json=openai_body,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta_text = chunk["choices"][0].get("delta", {}).get("content", "")
                    if delta_text:
                        output_tokens += 1
                        yield event(
                            "content_block_delta",
                            {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": delta_text},
                            },
                        )
                except Exception:
                    pass

    yield event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        },
    )
    yield event("message_stop", {"type": "message_stop"})


@app.post("/v1/messages")
async def messages(request: Request):
    body = await request.json()
    model = body.get("model", "local-model")
    stream = body.get("stream", False)

    openai_body = {
        "model": "local-model",
        "messages": to_openai_messages(body),
        "max_tokens": body.get("max_tokens", 4096),
        "stream": stream,
    }
    if body.get("temperature") is not None:
        openai_body["temperature"] = body["temperature"]

    if stream:
        return StreamingResponse(
            stream_anthropic(openai_body, model),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{MLX_URL}/v1/chat/completions",
            json=openai_body,
        )
        return JSONResponse(openai_resp_to_anthropic(resp.json(), model))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    print(f"Proxy on http://127.0.0.1:{PORT} → {MLX_URL}")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
