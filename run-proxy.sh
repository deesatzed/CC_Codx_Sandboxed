#!/bin/bash
# Optional. Default Claude path talks to mlx_vlm.server /v1/messages directly.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

export MLX_URL="http://${MLX_HOST}:${MLX_PORT}"
export PROXY_PORT

if ! curl -sf "${MLX_URL}/health" >/dev/null; then
  echo "FAIL: mlx server not reachable at ${MLX_URL}/health" >&2
  echo "  Start ./run-mlx.sh first." >&2
  exit 1
fi

exec "$VENV_PY" "${SCRIPT_DIR}/proxy.py"
