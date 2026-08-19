#!/bin/bash
# Prove the local server answers Anthropic /v1/messages with the loaded model.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

URL="http://${MLX_HOST}:${MLX_PORT}"

echo "Checking ${URL}/health ..."
curl -sf "${URL}/health" | "$VENV_PY" -c 'import json,sys; d=json.load(sys.stdin); print("loaded:", d.get("loaded_model")); raise SystemExit(0 if "Abliterated" in str(d.get("loaded_model","")) else 1)'

echo "Sending a 16-token ping to /v1/messages (uses your running 27B) ..."
code="$(curl -sS -o /tmp/claude-mlx-doctor.json -w '%{http_code}' \
  -X POST "${URL}/v1/messages" \
  -H 'content-type: application/json' \
  -H 'x-api-key: local-secret' \
  -H 'anthropic-version: 2023-06-01' \
  -d "{\"model\":\"${MODEL_DIR}\",\"max_tokens\":16,\"messages\":[{\"role\":\"user\",\"content\":\"Say the word ping.\"}]}")"

echo "HTTP ${code}"
"$VENV_PY" - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("/tmp/claude-mlx-doctor.json").read_text())
if d.get("type") == "error":
    raise SystemExit(f"server error: {d}")
text = "".join(b.get("text","") for b in d.get("content",[]) if isinstance(b, dict))
print("reply:", text.strip())
print("model:", d.get("model"))
if "ping" not in text.lower():
    raise SystemExit("reply did not contain 'ping'")
PY

echo
echo "Server is local and working."
echo "Claude Code is only local if its banner does NOT say Opus 5 / API Usage Billing."
echo "Quit that Claude (Ctrl+C) and run: ./run-claude.sh"
