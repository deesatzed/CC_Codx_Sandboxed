#!/bin/bash
# Live hop tape. Requires ./run-router.sh. Local half needs ./run-mlx.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=paths.sh
source "${SCRIPT_DIR}/paths.sh"

if ! curl -sf "http://127.0.0.1:${ROUTER_PORT:-4000}/health" >/dev/null; then
  echo "FAIL: hybrid router not on :${ROUTER_PORT:-4000}. Start ./run-router.sh." >&2
  exit 1
fi

echo "POST /v1/doctor/receipt  (OpenRouter ping, then real closed-port R1, then mlx)"
code="$(curl -sS -o /tmp/doctor-receipt.json -w '%{http_code}' \
  -X POST "http://127.0.0.1:${ROUTER_PORT:-4000}/v1/doctor/receipt")"
echo "HTTP ${code}"
"$VENV_PY" - <<'PY'
import json
from pathlib import Path
p = Path("/tmp/doctor-receipt.json")
d = json.loads(p.read_text())
print(json.dumps(d, indent=2)[:4000])
hop_a = d.get("hop_a") or {}
hop_b = d.get("hop_b") or {}
if hop_a.get("via") not in {"openrouter", "local"}:
    raise SystemExit("hop A missing via")
if hop_b.get("reason") != "R1":
    raise SystemExit(f"hop B must be real R1, got {hop_b!r}")
if not hop_b.get("closed_port_error"):
    raise SystemExit("hop B did not get a real closed-port error")
if hop_b.get("local_ok"):
    print("LOCAL: mlx answered after R1")
else:
    print("LOCAL: mlx did not answer (start ./run-mlx.sh for the full tape)")
print("latest hop also in receipts/hops.jsonl")
PY
