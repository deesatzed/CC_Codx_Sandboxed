# claude-mlx-sandbox

Claude Code + Codex, OS-sandboxed to this folder, talking to a hybrid router (OpenRouter first, local **Qwen 3.8 27B Abliterated MLX 4bit** on refusal).

This is **not** `claude-llamafile-sandbox`. Those scripts expect GGUF. The weights are MLX VLM shards (not in this git repo).

Remote: `https://github.com/deesatzed/CC_Codx_Sandboxed.git`

## Clone on another Mac

This repo is the **launcher**, not the 27B weights and not your OpenRouter key.

```bash
git clone https://github.com/deesatzed/CC_Codx_Sandboxed.git
cd CC_Codx_Sandboxed
cp .env.example .env
# paste OPENROUTER_API_KEY
# if this Mac is not /Volumes/WS4TB/q38Ablit, set Q38_ROOT, VENV_PY, MODEL_DIR
./setup.sh
./check.sh
```

Also needed on that Mac (not git):

- `claude` and `codex` on PATH
- `safehouse` (`./setup.sh` installs it)
- q38Ablit `.venv` with `mlx_vlm`
- the Abliterated 4bit directory (same layout as `MODEL_DIR`)

Then the four terminals in **Run** below. `./check-codex.sh` is the offline Codex-tool gate.

Do not copy `.env` or `.codex-home/` between machines (keys and session logs).

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

If Codex `exec` returns `aborted` and the model only lists web-search / collaboration tools, quit that Codex window and run `./check-codex.sh` then `./run-codex.sh` again. The catalog must not use GPT-5.6 `tool_mode=code_mode_only` (that hides shell from OpenRouter models). Also restart `./run-router.sh` if you want inbound tool names printed in the router log.

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
