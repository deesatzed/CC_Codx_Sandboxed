# Claude + local Qwen 3.8 27B (MLX) sandbox — design

Date: 2026-08-19  
Status: approved  
Workspace: `/Volumes/WS4TB/q38Ablit/claude-mlx-sandbox`

## Problem

Option #3 (`claude-llamafile-sandbox`) assumes a GGUF/llamafile server. The models on this machine are MLX:

- Default (approved): `models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit` (~15G, complete shards)
- Not default: `models/mlx-community--Qwen3.8-27B-OptiQ-4bit` (needs `mlx-optiq`, out of this build)

`cli-chat.py` already loads Abliterated 4bit with `mlx_vlm.load`. The config is `Qwen3_5ForConditionalGeneration` (VLM). Vanilla `mlx_lm.server` is the wrong server.

## Success (pass/fail)

1. `./check.sh` exits 0: Safehouse present, Claude Code present, q38Ablit `.venv` imports `mlx_vlm`, 4bit shards match `model.safetensors.index.json`.
2. `./run-mlx.sh` listens on `127.0.0.1:8080` and `GET /health` returns ok. (Live; not run until asked.)
3. `./run-claude.sh` starts Claude Code inside Safehouse with `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`. A write outside the sandbox directory is denied.

Not success: downloading GGUF, using Pi, RAG, GC-A2A wiring, OptiQ serve, merging q38Ablit CLIs, claiming offline Claude is “production ready.”

## Architecture

```
Terminal 1: mlx_vlm.server :8080   (q38Ablit .venv, Abliterated 4bit)
Terminal 2: safehouse → claude     (ANTHROPIC_BASE_URL=http://127.0.0.1:8080)
            workdir = this directory only
```

`mlx_vlm.server` already implements `GET /health`, `POST /v1/messages` (Anthropic), and `POST /v1/chat/completions` (OpenAI). Default path does **not** need a proxy.

Optional: `./run-proxy.sh` on :4000 if Claude Code’s Anthropic dialect disagrees with mlx_vlm.

The MLX process is **not** sandboxed (it must read `../models/...`). Only Claude Code is sandboxed.

## Non-goals

- Pi / `pi-local-rag` / LFM2.5
- llamafile / GGUF download
- Attaching tools to GC-A2A population agents
- Editing `cli-chat.py` / `cliPchat.py` / `cliPC2chat.py`
- Starting the 27B server as part of writing these files

## Model

| Knob | Value |
|------|--------|
| Path | `/Volumes/WS4TB/q38Ablit/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit` |
| Loader | `/Volumes/WS4TB/q38Ablit/.venv/bin/python -m mlx_vlm.server` |
| Bind | `127.0.0.1` only |
| Port | `8080` (`MLX_PORT`) |

User-selected. Do not substitute another id without asking.

## Isolation

Safehouse `--workdir` = this directory. `--dangerously-skip-permissions` only after `safehouse` is on PATH. Nested git so files do not enter `qwentient64`. Parent `.gitignore` lists `/claude-mlx-sandbox/`.
