#!/bin/bash
# Parallel Codex launcher: same hybrid router + Safehouse + command files.
# Isolated CODEX_HOME so this does not change ~/.codex/config.toml.
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
if ! command -v codex >/dev/null; then
  echo "FAIL: codex not on PATH" >&2
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  echo "FAIL: .env missing. Copy .env.example and set OPENROUTER_API_KEY." >&2
  exit 1
fi

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
# Codex resolves this path as-is; pin it to this checkout (second Mac / moved folder).
sed -i.bak "s|^model_catalog_json = .*|model_catalog_json = \"${SCRIPT_DIR}/model-catalog.json\"|" \
  "${CODEX_HOME_DIR}/config.toml"
rm -f "${CODEX_HOME_DIR}/config.toml.bak"

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
if [[ -f "${SCRIPT_DIR}/slash/local.md" ]]; then
  cp "${SCRIPT_DIR}/slash/local.md" "${CODEX_HOME_DIR}/prompts/local.md"
fi
(cd "$SCRIPT_DIR" && "$VENV_PY" -c "from witness import append_witness; append_witness(host='codex', event='session_start', path='.')") || true

NODE_BIN="$(dirname "$(command -v node)")"
CODEX_BIN="$(dirname "$(command -v codex)")"

ENV_FILE="$(mktemp)"
cat > "$ENV_FILE" <<EOF
export PATH="${CODEX_BIN}:${NODE_BIN}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="${HOME}"
export USER="${USER}"
export LOGNAME="${USER}"
export SHELL="/bin/zsh"
export TMPDIR="/tmp"
export TMP="/tmp"
export TERM="${TERM:-xterm-256color}"
export LANG="${LANG:-en_US.UTF-8}"
export PWD="${SCRIPT_DIR}"
export OLDPWD="${SCRIPT_DIR}"
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
# Do not --env-pass TMPDIR: the host value is /var/folders/... and a previous
# launcher overwrite made child shells leave the granted workdir temp.
# Process cwd must be SCRIPT_DIR: Safehouse --workdir grants that path; getcwd
# / `ls .` fail if Codex is started from an ungranted directory.
cd "$SCRIPT_DIR"
exec safehouse \
  --workdir "$SCRIPT_DIR" \
  --add-dirs-ro "${HOME}/.nvm" \
  --add-dirs-ro "${HOME}/.local" \
  --add-dirs "/tmp" \
  --env="$ENV_FILE" \
  --env-pass HOME,USER,LOGNAME,TERM,LANG \
  --enable process-control \
  -- /bin/zsh -c "cd $(printf '%q' "$SCRIPT_DIR") && exec codex --dangerously-bypass-approvals-and-sandbox -C $(printf '%q' "$SCRIPT_DIR")"
