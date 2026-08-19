#!/bin/bash
# Hybrid router: OpenRouter first, compressed local MLX on refusal.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  echo "FAIL: ${SCRIPT_DIR}/.env missing. Copy .env.example and set OPENROUTER_API_KEY." >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a
source "${SCRIPT_DIR}/.env"
set +a

if [[ -z "${OPENROUTER_MODEL:-}" ]]; then
  echo "FAIL: OPENROUTER_MODEL unset in .env" >&2
  exit 1
fi
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "FAIL: OPENROUTER_API_KEY unset in .env" >&2
  exit 1
fi

echo "Starting hybrid-router on 127.0.0.1:${ROUTER_PORT:-4000}"
echo "  OpenRouter: ${OPENROUTER_MODEL}"
echo "  Local:      ${MODEL_DIR}"
echo "Leave ./run-mlx.sh running if you want refusal fallback."

cd "$SCRIPT_DIR"
exec "$VENV_PY" "${SCRIPT_DIR}/router.py"
