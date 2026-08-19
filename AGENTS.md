# claude-mlx-sandbox (Codex)

This folder is OS-sandboxed. Stay inside this directory (including `repoShowP1/`).

You have a local shell (`exec` / `shell_command`) and `apply_patch`. Use them for file work. Do not spawn sub-agents. Do not use web search to inspect this folder.

Model traffic goes to `127.0.0.1:4000` (hybrid router): OpenRouter `deepseek/deepseek-v4-pro-0813` first; refusals go to local Abliterated Qwen 3.8 27B 4bit.

Custom prompts were copied from `~/.claude/commands` into `$CODEX_HOME/prompts`. In Codex they are **`$name`**, not `/name`. Examples: `$build`, `$discovery`, `$legacy-interview`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
