#!/bin/bash
# Offline readiness. Does not load the 27B model.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

echo "=== claude-mlx-sandbox check ==="

[[ -x "$VENV_PY" ]] || fail "q38Ablit venv missing: $VENV_PY"
ok "venv $VENV_PY"

"$VENV_PY" -c "import mlx_vlm.server" || fail "mlx_vlm.server not importable in venv"
ok "mlx_vlm.server import"

[[ -d "$MODEL_DIR" ]] || fail "model dir missing: $MODEL_DIR"
ok "model dir $MODEL_DIR"

"$VENV_PY" - <<PY || fail "model shards incomplete"
import json, sys
from pathlib import Path
d = Path("$MODEL_DIR")
index = json.loads((d / "model.safetensors.index.json").read_text())
missing = []
for name in set((index.get("weight_map") or {}).values()):
    p = d / name
    if not p.is_file() or p.stat().st_size <= 0:
        missing.append(name)
if missing:
    print("missing", missing)
    sys.exit(1)
print("shards", len(set((index.get("weight_map") or {}).values())))
PY
ok "Abliterated 4bit shards present"

command -v claude >/dev/null || fail "claude not on PATH (expected ~/.local/bin/claude)"
ok "claude $(command -v claude)"

if command -v safehouse >/dev/null; then
  ok "safehouse $(command -v safehouse)"
else
  fail "safehouse not installed. Run ./setup.sh"
fi

command -v node >/dev/null || fail "node not on PATH"
ok "node $(node -v)"

"$VENV_PY" -c "import fastapi, uvicorn, httpx" || fail "proxy deps missing in venv"
ok "proxy deps (optional path)"

echo "=== check passed (no 27B load) ==="
