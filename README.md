# claude-mlx-sandbox

Claude Code, offline, against local **Qwen 3.8 27B Abliterated MLX 4bit**, OS-sandboxed to this folder.

This is **not** `claude-llamafile-sandbox`. Those scripts expect GGUF. The weights on this machine are MLX VLM shards already used by `/Volumes/WS4TB/q38Ablit/cli-chat.py`.

## Run (after `./setup.sh` and `./check.sh`)

```bash
# Terminal 1
./run-mlx.sh

# Terminal 2 — after curl http://127.0.0.1:8080/health works
./run-claude.sh
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
