#!/bin/bash
# Start Claude Code inside Safehouse, pointed at the local MLX server.
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

if ! command -v safehouse >/dev/null; then
  echo "FAIL: safehouse not on PATH. Run ./setup.sh" >&2
  exit 1
fi
if ! command -v claude >/dev/null; then
  echo "FAIL: claude not on PATH" >&2
  exit 1
fi

# Default: hybrid router :4000 (OpenRouter first, local on refusal).
# USE_LOCAL=1 → talk to mlx_vlm :8080 only (slow prefills).
# USE_PROXY=1 → old Anthropic→OpenAI proxy (no OpenRouter).
if [[ "${USE_LOCAL:-0}" == "1" ]]; then
  ANTHROPIC_BASE_URL="http://${MLX_HOST}:${MLX_PORT}"
elif [[ "${USE_PROXY:-0}" == "1" ]]; then
  ANTHROPIC_BASE_URL="http://127.0.0.1:${PROXY_PORT}"
else
  ANTHROPIC_BASE_URL="http://127.0.0.1:${PROXY_PORT}"
fi

# mlx_vlm.server treats the request "model" field as a Hugging Face repo id
# unless it is the already-loaded path. "opus" / "local" makes it call the
# internet and 500. Pin every alias to the on-disk 4bit path.
LOCAL_MODEL="$MODEL_DIR"

if ! curl -sf "${ANTHROPIC_BASE_URL}/health" >/dev/null; then
  echo "FAIL: cannot reach ${ANTHROPIC_BASE_URL}/health" >&2
  echo "  Start ./run-router.sh (hybrid) or USE_LOCAL=1 with ./run-mlx.sh." >&2
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
export ANTHROPIC_MODEL="${LOCAL_MODEL}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${LOCAL_MODEL}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${LOCAL_MODEL}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${LOCAL_MODEL}"
export ANTHROPIC_SMALL_FAST_MODEL="${LOCAL_MODEL}"
export ANTHROPIC_DEFAULT_OPUS_MODEL_NAME="Qwen3.8-27B-Abliterated-4bit"
export ANTHROPIC_DEFAULT_SONNET_MODEL_NAME="Qwen3.8-27B-Abliterated-4bit"
export ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME="Qwen3.8-27B-Abliterated-4bit"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
EOF

USER_COMMANDS="${HOME}/.claude/commands"
PROJECT_COMMANDS="${SCRIPT_DIR}/.claude/commands"
if [[ -d "$USER_COMMANDS" ]]; then
  mkdir -p "$PROJECT_COMMANDS"
  if command -v rsync >/dev/null; then
    rsync -a --delete "$USER_COMMANDS/" "$PROJECT_COMMANDS/"
  else
    rm -rf "$PROJECT_COMMANDS"
    mkdir -p "$PROJECT_COMMANDS"
    cp -R "$USER_COMMANDS/." "$PROJECT_COMMANDS/"
  fi
  echo "Commands mirrored into .claude/commands/ from ${USER_COMMANDS}"
else
  echo "Note: ${USER_COMMANDS} not found; slash commands will be empty."
fi

echo
echo "Local brain: ${LOCAL_MODEL}"
echo "API:         ${ANTHROPIC_BASE_URL}"
echo
echo "If the Claude banner says 'Opus 5' or 'API Usage Billing', you are on the CLOUD."
echo "Quit that window (Ctrl+C) and run this script again."
echo "This launch uses --bare so it will not reuse your claude.ai login."
echo "Slash commands: type /build  (files live in this folder's .claude/commands/)"
echo

# Safehouse is the sandbox. --dangerously-skip-permissions is only valid here.
# Do not copy this flag to an unsandboxed claude invocation.
cleanup() { rm -f "$ENV_FILE"; }
trap cleanup EXIT

SAFEHOUSE_CMD=(
  safehouse
  --workdir "$SCRIPT_DIR"
  --add-dirs-ro "${HOME}/.nvm"
  --add-dirs-ro "${HOME}/.local"
)
if [[ -d "$USER_COMMANDS" ]]; then
  SAFEHOUSE_CMD+=(--add-dirs-ro "$USER_COMMANDS")
fi
SAFEHOUSE_CMD+=(--env="$ENV_FILE" --)

# --bare skips the automatic skill/command walk (that is why /build was
# missing). --plugin-dir is the documented way to load commands anyway.
# Layout: .claude/.claude-plugin/plugin.json + .claude/commands/*.md
CLAUDE_CMD=(
  claude
  --bare
  --model "$LOCAL_MODEL"
  --dangerously-skip-permissions
  --plugin-dir "${SCRIPT_DIR}/.claude"
)

exec "${SAFEHOUSE_CMD[@]}" "${CLAUDE_CMD[@]}"
