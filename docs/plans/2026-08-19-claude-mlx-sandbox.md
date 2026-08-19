# Claude MLX sandbox Implementation Plan

**Goal:** Give Claude Code a local Abliterated Qwen 3.8 27B 4-bit MLX server and OS sandbox, using weights already on disk.

**Architecture:** `mlx_vlm.server` (same family as `cli-chat.py`) on 127.0.0.1:8080; Claude Code pointed at that host’s `/v1/messages`; Safehouse restricts file access to this directory. Optional Anthropic→OpenAI proxy if the native Anthropic route fails.

**Tech Stack:** q38Ablit `.venv` (Python 3.14 + mlx_vlm), Claude Code, Agent Safehouse, bash.

No time estimates. No model download. No live 27B start in the write-files tasks.

---

### Task 1: Check model path and proxy helpers

**Files:**
- Create: `tests/test_model_path.py`
- Create: `tests/test_proxy.py`
- Create: `proxy.py`

Unit tests only. They must not load the 27B weights.

---

### Task 2: Scripts and checklist

**Files:**
- Create: `BUILD.md`
- Create: `setup.sh`
- Create: `check.sh`
- Create: `run-mlx.sh`
- Create: `run-claude.sh`
- Create: `run-proxy.sh`
- Create: `.safehouse`
- Create: `.gitignore`
- Create: `README.md`

---

### Task 3: Verify offline

**Commands:**
```bash
./check.sh
/Volumes/WS4TB/q38Ablit/.venv/bin/python -m pytest tests/ -q
```

Expected: `check.sh` exit 0 after Safehouse is installed; pytest all pass.

Live server start is a later, explicit step.
