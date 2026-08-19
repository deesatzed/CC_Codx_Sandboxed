#!/bin/bash
# Install only what this machine is missing. Never downloads model weights.
# Never pip-installs into Homebrew python3.14.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

echo "=== claude-mlx-sandbox setup ==="

if command -v safehouse >/dev/null; then
  echo "[OK] safehouse already on PATH"
else
  # Homebrew formula builds from source and fails on this Mac (Xcode 26.4
  # vs required 27). Upstream also ships a standalone script.
  echo "[Installing] agent-safehouse standalone script → ~/.local/bin/safehouse"
  mkdir -p "${HOME}/.local/bin"
  curl -fsSL "https://github.com/eugene1g/agent-safehouse/releases/latest/download/safehouse.sh" \
    -o "${HOME}/.local/bin/safehouse"
  chmod +x "${HOME}/.local/bin/safehouse"
  if ! command -v safehouse >/dev/null; then
    echo "FAIL: safehouse installed to ~/.local/bin but that dir is not on PATH"
    exit 1
  fi
fi

if command -v claude >/dev/null; then
  echo "[OK] claude $(claude --version 2>/dev/null | head -1)"
else
  echo "FAIL: install Claude Code first (npm i -g @anthropic-ai/claude-code)"
  echo "  This machine previously had it at ~/.local/bin/claude"
  exit 1
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "FAIL: q38Ablit venv not found at $VENV_PY"
  echo "  That project owns mlx_vlm. Recreate it there, do not pip into Homebrew 3.14."
  exit 1
fi

"$VENV_PY" -c "import mlx_vlm.server, fastapi, uvicorn, httpx" || {
  echo "FAIL: venv is missing mlx_vlm or proxy packages."
  echo "  Fix inside /Volumes/WS4TB/q38Ablit/.venv — not with Homebrew pip."
  exit 1
}

if [[ ! -f "${MODEL_DIR}/model.safetensors.index.json" ]]; then
  echo "FAIL: Abliterated 4bit missing at $MODEL_DIR"
  exit 1
fi

echo
echo "Setup complete. Next:"
echo "  ./check.sh"
echo "  ./run-mlx.sh          # Terminal 1 (loads ~15G 4bit; wait for listening)"
echo "  ./run-claude.sh       # Terminal 2"
echo
echo "Do not pass --dangerously-skip-permissions outside Safehouse."
