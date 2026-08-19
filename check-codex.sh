#!/bin/bash
# Offline Codex-tool checks. Does not start mlx or hit OpenRouter.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

"$VENV_PY" -m pytest "${SCRIPT_DIR}/tests/test_codex_tools.py" "${SCRIPT_DIR}/tests/test_responses.py" -q

CODEX_HOME_DIR="${SCRIPT_DIR}/.codex-home"
mkdir -p "${CODEX_HOME_DIR}"
cp "${SCRIPT_DIR}/codex-hybrid.toml" "${CODEX_HOME_DIR}/config.toml"

if command -v codex >/dev/null; then
  dumped="$(CODEX_HOME="${CODEX_HOME_DIR}" codex debug models 2>/dev/null || true)"
  echo "$dumped" | "$VENV_PY" -c '
import json, sys
raw = sys.stdin.read()
data = json.loads(raw)
models = data.get("models") or []
assert models, "debug models empty"
m = models[0]
assert "tool_mode" not in m, m
assert "multi_agent_version" not in m, m
assert m.get("shell_type") == "shell_command"
print("debug models:", m.get("slug"))
'
  ok "codex debug models has no code_mode_only"
else
  fail "codex not on PATH"
fi

if ! command -v safehouse >/dev/null; then
  fail "safehouse not on PATH"
fi

cd "$SCRIPT_DIR"
out="$(safehouse --workdir "$SCRIPT_DIR" --add-dirs /tmp --enable process-control -- /bin/zsh -c 'pwd; ls . | wc -l')"
echo "$out" | grep -q "$SCRIPT_DIR" || fail "safehouse pwd did not print workdir: $out"
echo "$out" | awk 'NR==2 && $1+0>5 {found=1} END{exit found?0:1}' || fail "safehouse ls . produced too few lines: $out"
ok "safehouse pwd/ls . from workdir"

echo "check-codex passed (no OpenRouter hop)"
