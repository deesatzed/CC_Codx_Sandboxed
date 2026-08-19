#!/bin/bash
# Start Claude Code inside Safehouse, pointed at the local MLX server.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

if ! command -v safehouse >/dev/null; then
  echo "FAIL: safehouse not on PATH. Run ./setup.sh" >&2
  exit 1
fi
if ! command -v claude >/dev/null; then
  echo "FAIL: claude not on PATH" >&2
  exit 1
fi

# USE_PROXY=1 → Anthropic proxy on PROXY_PORT; default is mlx_vlm native /v1/messages.
if [[ "${USE_PROXY:-0}" == "1" ]]; then
  ANTHROPIC_BASE_URL="http://127.0.0.1:${PROXY_PORT}"
else
  ANTHROPIC_BASE_URL="http://${MLX_HOST}:${MLX_PORT}"
fi

if ! curl -sf "${ANTHROPIC_BASE_URL}/health" >/dev/null; then
  echo "FAIL: cannot reach ${ANTHROPIC_BASE_URL}/health" >&2
  echo "  Start ./run-mlx.sh first (and ./run-proxy.sh if USE_PROXY=1)." >&2
  exit 1
fi

NODE_BIN="$(dirname "$(command -v node)")"
CLAUDE_BIN="$(dirname "$(command -v claude)")"

ENV_FILE="$(mktemp)"
cat > "$ENV_FILE" <<EOF
export PATH="${CLAUDE_BIN}:${NODE_BIN}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL}"
export ANTHROPIC_API_KEY="local-secret"
export ANTHROPIC_AUTH_TOKEN="local-secret"
EOF

# Safehouse is the sandbox. --dangerously-skip-permissions is only valid here.
# Do not copy this flag to an unsandboxed claude invocation.
cleanup() { rm -f "$ENV_FILE"; }
trap cleanup EXIT

exec safehouse \
  --workdir "$SCRIPT_DIR" \
  --add-dirs-ro "${HOME}/.nvm" \
  --add-dirs-ro "${HOME}/.local" \
  --env="$ENV_FILE" \
  -- claude --dangerously-skip-permissions
