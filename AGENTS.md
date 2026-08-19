# claude-mlx-sandbox (Codex)

This folder is OS-sandboxed. Stay inside this directory (including `repoShowP1/`).

Model traffic goes to `127.0.0.1:4000` (hybrid router): OpenRouter `deepseek/deepseek-v4-pro-0813` first; refusals go to local Abliterated Qwen 3.8 27B 4bit.

Custom prompts were copied from `~/.claude/commands` into `$CODEX_HOME/prompts`. In Codex they are **`$name`**, not `/name`. Examples: `$build`, `$discovery`, `$legacy-interview`.
