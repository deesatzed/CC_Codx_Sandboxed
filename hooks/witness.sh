#!/bin/bash
# Claude/Codex PreToolUse: append one witness line, never block the tool.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${1:-unknown}"
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi
# shellcheck source=../paths.sh
source "${ROOT}/paths.sh"
exec "$VENV_PY" "${ROOT}/witness.py" "$HOST"
