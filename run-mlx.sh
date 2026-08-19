#!/bin/bash
# Start mlx_vlm.server on the local Abliterated 4bit weights.
# This process is NOT sandboxed; it must read ../models/.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "${SCRIPT_DIR}/.env"
  set +a
fi
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

if [[ ! -x "$VENV_PY" ]]; then
  echo "FAIL: $VENV_PY missing" >&2
  exit 1
fi
if [[ ! -f "${MODEL_DIR}/model.safetensors.index.json" ]]; then
  echo "FAIL: model missing: $MODEL_DIR" >&2
  exit 1
fi

echo "Starting mlx_vlm.server"
echo "  python: $VENV_PY"
echo "  model:  $MODEL_DIR"
echo "  bind:   ${MLX_HOST}:${MLX_PORT}"
echo "Wait until GET http://${MLX_HOST}:${MLX_PORT}/health succeeds before run-claude.sh"

exec "$VENV_PY" -m mlx_vlm.server \
  --host "$MLX_HOST" \
  --port "$MLX_PORT" \
  --model "$MODEL_DIR" \
  --max-tokens "${MLX_MAX_TOKENS:-8192}"
