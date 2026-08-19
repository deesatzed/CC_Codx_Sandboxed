#!/bin/bash
# Parallel Codex launcher: same hybrid router + Safehouse + command files.
# Isolated CODEX_HOME so this does not change ~/.codex/config.toml.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

if ! command -v safehouse >/dev/null; then
  echo "FAIL: safehouse not on PATH. Run ./setup.sh" >&2
  exit 1
fi
if ! command -v codex >/dev/null; then
  echo "FAIL: codex not on PATH" >&2
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  echo "FAIL: .env missing" >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a
source "${SCRIPT_DIR}/.env"
set +a

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "FAIL: OPENROUTER_API_KEY unset in .env" >&2
  exit 1
fi
if [[ -z "${OPENROUTER_MODEL:-}" ]]; then
  echo "FAIL: OPENROUTER_MODEL unset in .env" >&2
  exit 1
fi

if ! curl -sf "http://127.0.0.1:${ROUTER_PORT:-4000}/health" >/dev/null; then
  echo "FAIL: hybrid router not on :${ROUTER_PORT:-4000}. Start ./run-router.sh first." >&2
  exit 1
fi

CODEX_HOME_DIR="${SCRIPT_DIR}/.codex-home"
mkdir -p "${CODEX_HOME_DIR}/prompts"
cp "${SCRIPT_DIR}/codex-hybrid.toml" "${CODEX_HOME_DIR}/config.toml"

USER_COMMANDS="${HOME}/.claude/commands"
if [[ -d "$USER_COMMANDS" ]]; then
  "$VENV_PY" - <<PY
from pathlib import Path
src = Path("${USER_COMMANDS}")
dest = Path("${CODEX_HOME_DIR}") / "prompts"
dest.mkdir(parents=True, exist_ok=True)
for p in src.rglob("*.md"):
    rel = p.relative_to(src)
    name = "-".join(rel.with_suffix("").parts) + ".md"
    dest.joinpath(name).write_bytes(p.read_bytes())
print("prompts", len(list(dest.glob("*.md"))))
PY
fi

NODE_BIN="$(dirname "$(command -v node)")"
CODEX_BIN="$(dirname "$(command -v codex)")"

ENV_FILE="$(mktemp)"
cat > "$ENV_FILE" <<EOF
export PATH="${CODEX_BIN}:${NODE_BIN}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export CODEX_HOME="${CODEX_HOME_DIR}"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"
export OPENROUTER_MODEL="${OPENROUTER_MODEL}"
EOF

echo
echo "Codex isolated home: ${CODEX_HOME_DIR}"
echo "Router:              http://127.0.0.1:${ROUTER_PORT:-4000}/v1"
echo "Model:               ${OPENROUTER_MODEL} (OpenRouter first; local on refusal)"
echo "Custom prompts:      \$build  \$discovery  \$legacy-interview   (not /build)"
echo
echo "Does NOT use ~/.codex/config.toml (no gpt-5.6-luna, no ChatGPT login for this window)."
echo

cleanup() { rm -f "$ENV_FILE"; }
trap cleanup EXIT

# Safehouse is the OS box. Codex's own sandbox is disabled so they do not fight.
exec safehouse \
  --workdir "$SCRIPT_DIR" \
  --add-dirs-ro "${HOME}/.nvm" \
  --add-dirs-ro "${HOME}/.local" \
  --env="$ENV_FILE" \
  -- codex --dangerously-bypass-approvals-and-sandbox -C "$SCRIPT_DIR"
