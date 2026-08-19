#!/bin/bash
# Honest Safehouse tape. Reports what the policy actually does.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v safehouse >/dev/null; then
  echo "FAIL: safehouse not on PATH. Run ./setup.sh" >&2
  exit 1
fi

echo "workdir: $SCRIPT_DIR"
echo
echo "=== policy excerpts (file + network + tmp) ==="
safehouse --workdir "$SCRIPT_DIR" --stdout 2>/dev/null | \
  grep -E 'process-exec|subpath "/private/tmp"|subpath "/tmp"|network|huggingface|deny file-write|allow file-read\* file-write\* \(subpath' | head -40
echo

cd "$SCRIPT_DIR"
INSIDE="${SCRIPT_DIR}/.prove-inside.txt"
OUTSIDE="$(cd "$SCRIPT_DIR/.." && pwd)/.prove-outside-should-fail.txt"
rm -f "$INSIDE" "$OUTSIDE"

echo "=== 1. write inside workdir (must succeed) ==="
if safehouse --workdir "$SCRIPT_DIR" -- /bin/zsh -c "echo inside-ok > .prove-inside.txt"; then
  if grep -q inside-ok "$INSIDE" 2>/dev/null; then
    echo "PASS: workdir write"
  else
    echo "FAIL: command ok but file missing" >&2
    exit 1
  fi
else
  echo "FAIL: workdir write denied" >&2
  exit 1
fi

echo "=== 2. write parent of workdir (must fail) ==="
if safehouse --workdir "$SCRIPT_DIR" -- /bin/zsh -c "echo leak > ../.prove-outside-should-fail.txt" 2>/tmp/prove-outside.err; then
  if [[ -f "$OUTSIDE" ]]; then
    echo "FAIL: parent write succeeded — Safehouse did not box the workdir" >&2
    rm -f "$OUTSIDE"
    exit 1
  fi
  echo "PASS: command returned 0 but parent file was not created"
else
  echo "PASS: parent write denied"
  sed -n '1,8p' /tmp/prove-outside.err || true
fi
rm -f "$OUTSIDE"

echo "=== 3. /tmp write (Safehouse default is often ALLOW — do not fake a deny) ==="
if safehouse --workdir "$SCRIPT_DIR" -- /bin/zsh -c "echo tmp > /tmp/sandbox-tmp-probe.$$" 2>/tmp/prove-tmp.err; then
  echo "ALLOW: /tmp write (default Safehouse grants /private/tmp)"
  rm -f /tmp/sandbox-tmp-probe.$$
else
  echo "DENY: /tmp write"
  sed -n '1,8p' /tmp/prove-tmp.err || true
fi

echo "=== 4. outbound HTTPS to huggingface.co (default Safehouse often ALLOWs TCP) ==="
if safehouse --workdir "$SCRIPT_DIR" -- /usr/bin/curl -sI --max-time 8 https://huggingface.co >/tmp/prove-hf.out 2>/tmp/prove-hf.err; then
  echo "ALLOW: huggingface.co"
  head -2 /tmp/prove-hf.out
else
  echo "DENY or error: huggingface.co"
  sed -n '1,8p' /tmp/prove-hf.err || true
fi

rm -f "$INSIDE"
echo
echo "prove-sandbox finished. Workdir is boxed; /tmp and network are reported as they are."
