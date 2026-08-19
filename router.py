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
from graph_context import compact_subgraph, last_user_text
from receipts import consume_force_local, latest_hop, write_hop, write_refusal_if_real
from refusal import classify_refusal, is_refusal
from responses_bridge import compress_responses_for_local, responses_to_sse, wrap_chat_as_response
from shorthand import compress_for_local

ROOT = Path(__file__).resolve().parent


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


def _excerpt_body(body: dict | None) -> str:
    if not isinstance(body, dict):
        return ""
    err = body.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)[:500]
    if isinstance(body.get("content"), list):
        return "".join(
            str(b.get("text") or "") for b in body["content"] if isinstance(b, dict)
        )[:500]
    choices = body.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        c = msg.get("content")
        return (c if isinstance(c, str) else str(c or ""))[:500]
    return str(body.get("status") or "")[:200]


def _graph_injected(body: dict) -> bool:
    text = compact_subgraph(ROOT / "graphify-out" / "graph.json", last_user_text(body))
    return bool(text)


def _record(
    *,
    via: str,
    reason: str,
    route: str,
    or_status: int | None,
    err: BaseException | None,
    or_body: dict | None = None,
    local_body: dict | None = None,
    graph_injected: bool = False,
) -> dict:
    or_excerpt = _excerpt_body(or_body)
    if not or_excerpt and err is not None:
        or_excerpt = str(err)[:500]
    hop = write_hop(
        ROOT,
        via=via,
        reason=reason,
        route=route,
        or_status=or_status,
        err=type(err).__name__ if err else None,
        usage=(or_body or {}).get("usage") if isinstance(or_body, dict) else {},
        or_excerpt=or_excerpt,
        local_excerpt=_excerpt_body(local_body) if via == "local" else "",
        graph_injected=graph_injected,
    )
    write_refusal_if_real(ROOT, hop)
    return hop


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "openrouter_model": OPENROUTER_MODEL,
        "local_model": LOCAL_MODEL,
        "force_local": (ROOT / ".force-local").is_file(),
        "graph": (ROOT / "graphify-out" / "graph.json").is_file(),
    }


@app.get("/v1/receipts/latest")
async def receipts_latest():
    rec = latest_hop(ROOT)
    if rec is None:
        return JSONResponse({"error": "no hops yet"}, status_code=404)
    return rec


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
    injected = _graph_injected(body)

    if consume_force_local(ROOT):
        print("hop via=local reason=force-local")
        _record(
            via="local",
            reason="force-local",
            route="/v1/messages",
            or_status=None,
            err=None,
            graph_injected=injected,
        )
        return await _local_anthropic(body, stream=stream)

    status, or_body, err = await _openrouter_chat(oai)
    reason = classify_refusal(status, or_body, err, text_heuristic=TEXT_HEURISTIC)
    via = "local" if reason else "openrouter"
    print(f"hop via={via} reason={reason or 'ok'} or_status={status} err={type(err).__name__ if err else None}")

    if reason:
        _record(
            via="local",
            reason=reason,
            route="/v1/messages",
            or_status=status,
            err=err,
            or_body=or_body if isinstance(or_body, dict) else None,
            graph_injected=injected,
        )
        return await _local_anthropic(body, stream=stream)

    _record(
        via="openrouter",
        reason="ok",
        route="/v1/messages",
        or_status=status,
        err=None,
        or_body=or_body if isinstance(or_body, dict) else None,
        graph_injected=False,
    )
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

    injected = _graph_injected(body)
    if consume_force_local(ROOT):
        print("responses hop via=local reason=force-local")
        _record(
            via="local",
            reason="force-local",
            route="/v1/responses",
            or_status=None,
            err=None,
            graph_injected=injected,
        )
        return await _local_responses(body, stream=stream)

    status, or_body, err = await _openrouter_responses(body)
    reason = classify_refusal(status, or_body, err, text_heuristic=TEXT_HEURISTIC)
    via = "local" if reason else "openrouter"
    print(f"responses hop via={via} reason={reason or 'ok'} or_status={status} err={type(err).__name__ if err else None}")

    if reason:
        _record(
            via="local",
            reason=reason,
            route="/v1/responses",
            or_status=status,
            err=err,
            or_body=or_body if isinstance(or_body, dict) else None,
            graph_injected=injected,
        )
        return await _local_responses(body, stream=stream)

    _record(
        via="openrouter",
        reason="ok",
        route="/v1/responses",
        or_status=status,
        err=None,
        or_body=or_body if isinstance(or_body, dict) else None,
    )
    if stream:
        return Response(content=responses_to_sse(or_body or {}), media_type="text/event-stream")
    return JSONResponse(or_body or {})


@app.post("/v1/doctor/receipt")
async def doctor_receipt():
    """Live tape: OpenRouter ping, then a real closed-port R1, then mlx if up."""
    _require_config()
    ping = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": "Say the word ping."}],
        "max_tokens": 16,
    }
    status, or_body, err = await _openrouter_chat(ping)
    reason_a = classify_refusal(status, or_body, err, text_heuristic=TEXT_HEURISTIC)
    _record(
        via="local" if reason_a else "openrouter",
        reason=reason_a or "ok",
        route="/v1/doctor/receipt",
        or_status=status,
        err=err,
        or_body=or_body if isinstance(or_body, dict) else None,
        local_body=None,
    )

    closed_err: BaseException | None = None
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            await client.post("http://127.0.0.1:9/v1/chat/completions", json={"n": 1})
    except BaseException as exc:
        closed_err = exc
    reason_b = classify_refusal(None, None, closed_err) or "R1"

    local_ok = False
    local_body: dict | None = None
    mlx_err: BaseException | None = None
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{MLX_URL}/v1/messages",
                json={
                    "model": LOCAL_MODEL,
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": "Say the word pong."}],
                },
                headers={"content-type": "application/json", "x-api-key": "local-secret"},
            )
            try:
                local_body = resp.json()
            except Exception:
                local_body = {"error": {"message": resp.text[:400]}}
            local_ok = resp.status_code < 400 and isinstance(local_body, dict) and local_body.get("type") != "error"
    except BaseException as exc:
        mlx_err = exc
        local_body = {"error": {"message": str(exc)[:400]}}

    _record(
        via="local",
        reason=reason_b,
        route="/v1/doctor/receipt",
        or_status=None,
        err=closed_err,
        or_body={"error": {"message": str(closed_err)[:400] if closed_err else "closed-port unexpected success"}},
        local_body=local_body if isinstance(local_body, dict) else None,
    )
    return {
        "hop_a": {"via": "local" if reason_a else "openrouter", "reason": reason_a or "ok", "or_status": status},
        "hop_b": {
            "reason": reason_b,
            "closed_port_error": type(closed_err).__name__ if closed_err else None,
            "local_ok": local_ok,
            "mlx_error": type(mlx_err).__name__ if mlx_err else None,
            "local_excerpt": _excerpt_body(local_body if isinstance(local_body, dict) else None),
        },
        "latest": latest_hop(ROOT),
    }


if __name__ == "__main__":
    import uvicorn

    _require_config()
    uvicorn.run(app, host="127.0.0.1", port=ROUTER_PORT)
