#!/usr/bin/env python3
"""Claude Code → OpenRouter first; on defined refusal, compressed local MLX."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from anthropic_openai import anthropic_to_sse, openai_chat_to_anthropic, to_openai_chat
from refusal import is_refusal
from responses_bridge import compress_responses_for_local, responses_to_sse, wrap_chat_as_response
from shorthand import compress_for_local


def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


_load_env(Path(__file__).resolve().parent / ".env")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "").strip()
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
MLX_URL = os.environ.get("MLX_URL", "http://127.0.0.1:8080").rstrip("/")
LOCAL_MODEL = os.environ.get(
    "LOCAL_MODEL",
    "/Volumes/WS4TB/q38Ablit/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit",
)
ROUTER_PORT = int(os.environ.get("ROUTER_PORT", "4000"))
TEXT_HEURISTIC = os.environ.get("REFUSAL_TEXT_HEURISTIC", "0") in {"1", "true", "yes"}

app = FastAPI()


@app.middleware("http")
async def _log_every_request(request: Request, call_next):
    print(f"IN {request.method} {request.url.path} qs={request.url.query!r}")
    response = await call_next(request)
    print(f"OUT {response.status_code} {request.method} {request.url.path}")
    return response


def _require_config() -> None:
    if not OPENROUTER_MODEL:
        raise RuntimeError("OPENROUTER_MODEL is unset. Set it in .env — this process will not pick a model.")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is unset. Put it in .env (gitignored).")


@app.on_event("startup")
async def startup() -> None:
    _require_config()
    print(f"hybrid-router :{ROUTER_PORT}")
    print(f"  OpenRouter model: {OPENROUTER_MODEL}")
    print(f"  local fallback:   {LOCAL_MODEL}")
    print(f"  mlx:              {MLX_URL}")


@app.get("/health")
async def health():
    return {"status": "ok", "openrouter_model": OPENROUTER_MODEL, "local_model": LOCAL_MODEL}


@app.get("/v1/responses")
@app.get("/v1/responses/")
@app.get("/responses")
@app.get("/responses/")
async def get_responses():
    """Codex probes this URL. POST is the real create; GET must not 404."""
    return {"object": "list", "data": []}


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    """Codex looks here for model metadata. One OpenRouter id + the local path."""
    now = 0
    return {
        "object": "list",
        "data": [
            {
                "id": OPENROUTER_MODEL,
                "object": "model",
                "created": now,
                "owned_by": "openrouter",
                "context_window": 128000,
                "max_output_tokens": 8192,
            },
            {
                "id": LOCAL_MODEL,
                "object": "model",
                "created": now,
                "owned_by": "local",
                "context_window": 262144,
                "max_output_tokens": 8192,
            },
        ],
    }


async def _openrouter_chat(oai_body: dict) -> tuple[int | None, dict | None, BaseException | None]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "claude-mlx-sandbox",
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=oai_body,
                headers=headers,
            )
            try:
                body = resp.json()
            except Exception:
                body = {"error": {"message": resp.text[:500]}}
            if not isinstance(body, dict):
                body = {"error": {"message": "non-object json"}}
            return resp.status_code, body, None
    except BaseException as exc:
        return None, None, exc


async def _local_anthropic(body: dict, *, stream: bool):
    compressed = compress_for_local(body, local_model=LOCAL_MODEL)
    compressed["stream"] = stream
    headers = {"content-type": "application/json", "x-api-key": "local-secret"}
    if stream:

        async def gen():
            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream(
                    "POST",
                    f"{MLX_URL}/v1/messages",
                    json=compressed,
                    headers=headers,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(gen(), media_type="text/event-stream")
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{MLX_URL}/v1/messages",
            json=compressed,
            headers=headers,
        )
        try:
            payload = resp.json()
        except Exception:
            payload = {"type": "error", "error": {"message": resp.text[:500]}}
        return JSONResponse(payload, status_code=resp.status_code)


@app.post("/v1/messages")
async def messages(request: Request):
    _require_config()
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"type": "error", "error": {"message": "body must be object"}}, status_code=400)
    stream = bool(body.get("stream"))

    oai = to_openai_chat(body, model=OPENROUTER_MODEL)
    oai["max_tokens"] = min(int(oai.get("max_tokens") or 4096), 8192)
    status, or_body, err = await _openrouter_chat(oai)
    fallback = is_refusal(status, or_body, err, text_heuristic=TEXT_HEURISTIC)
    via = "local" if fallback else "openrouter"
    print(f"hop via={via} or_status={status} err={type(err).__name__ if err else None}")

    if fallback:
        return await _local_anthropic(body, stream=stream)

    msg = openai_chat_to_anthropic(or_body or {}, model=OPENROUTER_MODEL)
    if stream:
        return Response(content=anthropic_to_sse(msg), media_type="text/event-stream")
    return JSONResponse(msg)


def _or_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "claude-mlx-sandbox",
    }


async def _openrouter_responses(body: dict) -> tuple[int | None, dict | None, BaseException | None]:
    payload = dict(body)
    payload["model"] = OPENROUTER_MODEL
    payload["stream"] = False
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/responses",
                json=payload,
                headers=_or_headers(),
            )
            try:
                data = resp.json()
            except Exception:
                data = {"error": {"message": resp.text[:500]}}
            if not isinstance(data, dict):
                data = {"error": {"message": "non-object json"}}
            return resp.status_code, data, None
    except BaseException as exc:
        return None, None, exc


async def _local_responses(body: dict, *, stream: bool):
    compressed = compress_responses_for_local(body, local_model=LOCAL_MODEL)
    compressed["stream"] = False
    headers = {"content-type": "application/json", "authorization": "Bearer local-secret"}
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(f"{MLX_URL}/v1/responses", json=compressed, headers=headers)
        try:
            data = resp.json()
        except Exception:
            data = None
        if resp.status_code >= 400 or not isinstance(data, dict) or data.get("error"):
            # Fall back to chat completions if mlx Responses is unhappy.
            inp = compressed.get("input")
            text = inp if isinstance(inp, str) else json.dumps(inp)
            chat_body = {
                "model": LOCAL_MODEL,
                "messages": [
                    {"role": "system", "content": compressed.get("instructions") or ""},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 2048,
                "stream": False,
            }
            chat = await client.post(f"{MLX_URL}/v1/chat/completions", json=chat_body, headers=headers)
            try:
                chat_json = chat.json()
            except Exception:
                chat_json = {"choices": [{"message": {"content": chat.text[:500]}}]}
            data = wrap_chat_as_response(chat_json if isinstance(chat_json, dict) else {}, model=LOCAL_MODEL)
    if stream:
        return Response(content=responses_to_sse(data), media_type="text/event-stream")
    return JSONResponse(data)


@app.post("/v1/responses")
@app.post("/v1/responses/")
@app.post("/responses")
@app.post("/responses/")
async def responses(request: Request):
    _require_config()
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"error": {"message": "body must be object"}}, status_code=400)
    stream = bool(body.get("stream"))
    tool_names: list[str] = []
    for tool in body.get("tools") or []:
        if isinstance(tool, dict):
            tool_names.append(str(tool.get("name") or tool.get("type") or "?"))
    print(f"responses tools n={len(tool_names)} names={tool_names[:40]}")

    status, or_body, err = await _openrouter_responses(body)
    fallback = is_refusal(status, or_body, err, text_heuristic=TEXT_HEURISTIC)
    if isinstance(or_body, dict) and or_body.get("status") in {"failed", "cancelled"}:
        fallback = True
    via = "local" if fallback else "openrouter"
    print(f"responses hop via={via} or_status={status} err={type(err).__name__ if err else None}")

    if fallback:
        return await _local_responses(body, stream=stream)

    if stream:
        return Response(content=responses_to_sse(or_body or {}), media_type="text/event-stream")
    return JSONResponse(or_body or {})


if __name__ == "__main__":
    import uvicorn

    _require_config()
    uvicorn.run(app, host="127.0.0.1", port=ROUTER_PORT)
