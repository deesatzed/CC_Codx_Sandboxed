# Hybrid router + local shorthand — design

Date: 2026-08-19  
Status: implemented (needs OPENROUTER_API_KEY in .env). Fast model: deepseek/deepseek-v4-pro-0813 (user-selected).  
Workspace: `/Volumes/WS4TB/q38Ablit/claude-mlx-sandbox`

## Problem

One Claude Code user turn is many `/v1/messages` hops. On the local 27B, **prefill** dominates:

- Hop 1: `prompt_tokens=14900`, prefill ~130 s, `cached_tokens=0`, then `tool_use`
- Hop 2: `prompt_tokens=19539`, full prefill again

Cloud/OpenRouter can ingest 15k tokens in seconds. The local Abliterated 4bit is still the right place for **refusals / uncensored / offline fallback**, but it must not re-eat the fat Claude Code system+tool blob.

## Success (pass/fail)

1. Claude Code talks only to `127.0.0.1:4000` (this router). Banner is **not** Opus 5 / API Usage Billing.
2. A normal hop completes via **OpenRouter** in seconds, not ~2 minutes.
3. A **defined refusal** (below) is retried on local Abliterated 4bit **without** sending the unmodified 15k prompt. Local `prompt_tokens` on that retry is **much smaller** than 14900 (target: system+tools stub under ~2k tokens, plus truncated history).
4. OpenRouter model id is **not hardcoded**. Process will not start if `OPENROUTER_MODEL` is unset.
5. No new model download. Local path stays  
   `/Volumes/WS4TB/q38Ablit/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit`.

Not success: guessing refusals from vibes; mid-stream switch to Claude Code; piping GC-A2A agents through this; claiming air-gap.

## Architecture

```
Claude Code  --Anthropic /v1/messages, stream=true-->
    127.0.0.1:4000  hybrid-router
         │
         ├─ 1. Buffer request
         ├─ 2. POST full request to OpenRouter (complete, then replay as SSE)
         │      OK → stream that answer to Claude Code. Stop.
         │      REFUSAL / transport error → step 3
         └─ 3. Shorthand-compress request
                POST to mlx_vlm.server :8080 with model = on-disk 4bit path
                Stream local tokens to Claude Code
```

`mlx_vlm.server` stays on **8080**. Claude’s `ANTHROPIC_BASE_URL` becomes **4000**. Same Safehouse workdir as today.

OpenRouter side uses an Anthropic- or OpenAI-compatible chat API. If the user-picked model is OpenAI-style, the existing `proxy.py` translation (messages + tool_calls ↔ tool_use) is required. If the model already speaks `/v1/messages`, pass through.

## What “refusal” means (v1, exact)

Treat as fallback to local **only** if one of these is true:

| Code | Trigger |
|------|---------|
| R1 | OpenRouter HTTP 401/402/403/408/429/5xx, or connect/timeout |
| R2 | JSON `error` with type/code indicating moderation, policy, or `content_filter` |
| R3 | Message `stop_reason` / `finish_reason` in `{content_filter, refusal}` |
| R4 | **Optional flag**, default **off**: assistant text matches a small denylist (`I cannot`, `I'm unable to`, `against my guidelines`) — too sloppy for default |

Not a refusal: slow OpenRouter, weak answer, wrong tool, local already running. User can later add an explicit `/local` override (R5) as a follow-on.

v1 does **not** switch mid-stream. OpenRouter is waited until a complete message (or error). Then we either replay that message as SSE to Claude Code, or start a **new** local stream. Claude Code never sees half a cloud sentence then a local continuation.

## Shorthand (local path only)

OpenRouter keeps the full Claude Code prompt (it can afford 15k).

**Only the local retry** is compressed, in this order:

1. **Replace** the huge Claude Code system prompt with a short stub (~300–800 tokens): you are a coding agent, use Anthropic `tool_use` blocks, prefer small Reads, do not claim to be Opus.
2. **Collapse tool schemas** to name + one-line + required args. Full JSON schemas are most of the 15k. Claude Code still understands `tool_use` by name.
3. **Truncate fat tool results** in history (e.g. keep head+tail of any tool payload over N characters). The hop-2 jump 14900→19539 was likely a dump.
4. **Do not** use q38Ablit SLC (`prompts/slc_payload.txt`) as the Claude Code system prompt. SLC is a different contract (Plinian/Autopoietic). Mixing it would change behavior, not just shrink tokens. Optional later, out of v1.

This is “shorthand” as **lossy routing**, not a new language the 27B must learn.

Prompt **KV cache** on mlx_vlm (`cached_tokens`) is best-effort. Today it was 0 across hops. Compression is the guaranteed win; cache is a bonus if two compressed prefixes match.

## Config (no silent model pick)

Gitignored `.env` in the sandbox:

```
OPENROUTER_API_KEY=   # required for cloud path
OPENROUTER_MODEL=     # required; you set the exact id
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MLX_URL=http://127.0.0.1:8080
ROUTER_PORT=4000
REFUSAL_TEXT_HEURISTIC=0
```

`run-claude.sh` points `ANTHROPIC_BASE_URL` at the router, still `--model` = local 4bit path so a fallback never sends `opus` to mlx (that caused Hugging Face 401). OpenRouter uses `OPENROUTER_MODEL` regardless of that path.

## Privacy / billing (honest)

- Default hop: **prompt leaves the Mac** to OpenRouter.
- Fallback hop: local only.
- This is **not** the original “no API keys, fully offline” option #3. It is a speed/refusal hybrid.
- Safehouse still allows outbound TCP today, so even “local Claude” tools can fetch URLs. Unchanged in this design.

## Non-goals

- Starting or replacing the 27B process
- Pi / LFM2.5 RAG
- GC-A2A population agents
- Dropping `--bare` / mounting `~/.claude/commands` (separate decision)
- Implementing R4 text heuristics as default
- Hardcoding an OpenRouter model id

## Verification (when built)

- Unit: refusal classifier on canned HTTP bodies (no network).
- Unit: compressor reduces a fixture 15k-like Anthropic body; tool names preserved.
- Live (your key, your model): one `./doctor-router.sh` that sends “say ping” → OpenRouter path, elapsed seconds not minutes.
- Live fallback: with OpenRouter URL pointed at a closed port, same ping hits mlx and log shows compressed `prompt_tokens`.

## Open before implementation

You must supply `OPENROUTER_MODEL` (exact OpenRouter id). The router will not invent one.
