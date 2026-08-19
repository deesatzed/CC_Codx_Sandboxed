# Shared paths. Sourced by the other scripts. Do not execute.
# Override on another machine via .env: Q38_ROOT, VENV_PY, MODEL_DIR, LOCAL_MODEL.

Q38_ROOT="${Q38_ROOT:-/Volumes/WS4TB/q38Ablit}"
VENV_PY="${VENV_PY:-${Q38_ROOT}/.venv/bin/python}"
MODEL_DIR="${MODEL_DIR:-${Q38_ROOT}/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit}"
LOCAL_MODEL="${LOCAL_MODEL:-${MODEL_DIR}}"
MLX_HOST="${MLX_HOST:-127.0.0.1}"
MLX_PORT="${MLX_PORT:-8080}"
PROXY_PORT="${PROXY_PORT:-4000}"
