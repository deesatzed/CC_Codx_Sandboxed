# claude-mlx-sandbox

Claude Code, offline, against local **Qwen 3.8 27B Abliterated MLX 4bit**, OS-sandboxed to this folder.

This is **not** `claude-llamafile-sandbox`. Those scripts expect GGUF. The weights on this machine are MLX VLM shards already used by `/Volumes/WS4TB/q38Ablit/cli-chat.py`.

## Run (after `./setup.sh` and `./check.sh`)

Hybrid (fast path). After `.env` has your OpenRouter key and `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813`:

```bash
# Terminal 1 — local fallback (keep running)
./run-mlx.sh

# Terminal 2 — router
./run-router.sh

# Terminal 3 — Claude Code talks to :4000
./run-claude.sh

# Terminal 4 (optional) — Codex, same router and Safehouse
./run-codex.sh
```

Codex uses an isolated `CODEX_HOME` (does not edit `~/.codex/config.toml`). Custom prompts are `$build` / `$legacy-interview`, not `/build`. Restart `./run-router.sh` once so it serves Codex’s `/v1/responses` path.

Local only (slow prefills): `USE_LOCAL=1 ./run-claude.sh` with only Terminal 1.

If Claude’s header says **Opus 5** or **API Usage Billing**, that window is using your paid Anthropic account, not the Mac. Quit it (Ctrl+C) and run `./run-claude.sh` again. The script now passes `--bare` and `--model` so it cannot reuse the claude.ai login.

`./run-claude.sh` copies `~/.claude/commands/` into `.claude/commands/` and loads them with `--plugin-dir .claude` (needed because `--bare` skips the normal command walk). Restart `./run-claude.sh`, then type `/` and look for `build`.

Optional check that the Mac model answers (Terminal 1 must stay running):

```bash
./doctor.sh
```

Model: `/Volumes/WS4TB/q38Ablit/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit`  
Python: `/Volumes/WS4TB/q38Ablit/.venv/bin/python`

`--dangerously-skip-permissions` is passed only inside Safehouse. Do not use that flag on a bare `claude`.

## Optional proxy

`mlx_vlm.server` already has `POST /v1/messages`. If Claude Code still fails the Anthropic dialect:

```bash
./run-proxy.sh
USE_PROXY=1 ./run-claude.sh
```

## Not in this build

Pi, LFM2.5 RAG, OptiQ serve, llamafile/GGUF download, GC-A2A agent tools.

See `BUILD.md` and `docs/plans/2026-08-19-claude-mlx-sandbox-design.md`.
