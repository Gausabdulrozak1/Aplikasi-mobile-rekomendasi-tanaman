#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/workspace/TaniAdaptif}"
ENV_FILE="${ENV_FILE:-/workspace/taniadaptif-secrets/runtime.env}"
EVIDENCE_DIR="${EVIDENCE_DIR:-/workspace/taniadaptif-evidence}"
LOG_DIR="${LOG_DIR:-/workspace/taniadaptif-logs}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "STOP: runtime environment file not found at ${ENV_FILE}." >&2
  exit 1
fi
if [[ ! -f "${REPO_ROOT}/inference_api/app/main.py" ]]; then
  echo "STOP: repository not found at ${REPO_ROOT}." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${PUBLIC_API_BASE_URL:-}" ]]; then
  if [[ -z "${RUNPOD_POD_ID:-}" ]]; then
    echo "STOP: set PUBLIC_API_BASE_URL when RUNPOD_POD_ID is unavailable." >&2
    exit 1
  fi
  export PUBLIC_API_BASE_URL="https://${RUNPOD_POD_ID}-3000.proxy.runpod.net"
fi
export INFERENCE_API_BASE_URL="http://127.0.0.1:5000"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

mkdir -p "${EVIDENCE_DIR}" "${LOG_DIR}" "${GENERATED_DIR}"
cd "${REPO_ROOT}"

python inference_api/scripts/gpu_preflight.py \
  --output "${EVIDENCE_DIR}/gpu_preflight.json"

INFERENCE_PID=""
BACKEND_PID=""
cleanup() {
  [[ -n "${BACKEND_PID}" ]] && kill "${BACKEND_PID}" 2>/dev/null || true
  [[ -n "${INFERENCE_PID}" ]] && kill "${INFERENCE_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python -m uvicorn inference_api.app.main:app \
  --host 127.0.0.1 \
  --port 5000 \
  --workers 1 \
  >"${LOG_DIR}/inference.log" 2>&1 &
INFERENCE_PID=$!

READY=0
for _ in $(seq 1 180); do
  if ! kill -0 "${INFERENCE_PID}" 2>/dev/null; then
    echo "STOP: inference service exited during model loading." >&2
    tail -n 80 "${LOG_DIR}/inference.log" >&2
    exit 1
  fi
  if curl --silent --fail \
    --header "X-Inference-Token: ${INFERENCE_API_TOKEN}" \
    http://127.0.0.1:5000/ready >/dev/null; then
    READY=1
    break
  fi
  sleep 5
done
if [[ "${READY}" -ne 1 ]]; then
  echo "STOP: inference /ready did not pass within 15 minutes." >&2
  tail -n 80 "${LOG_DIR}/inference.log" >&2
  exit 1
fi

node backend-nodejs/src/index.js >"${LOG_DIR}/backend.log" 2>&1 &
BACKEND_PID=$!

BACKEND_READY=0
for _ in $(seq 1 30); do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "STOP: backend service exited during startup." >&2
    tail -n 80 "${LOG_DIR}/backend.log" >&2
    exit 1
  fi
  if curl --silent --fail http://127.0.0.1:3000/api/kesehatan >/dev/null && \
    curl --silent --fail \
      --header "X-Client-Token: ${BACKEND_VISUAL_API_TOKEN}" \
      http://127.0.0.1:3000/api/visual/ready >/dev/null; then
    BACKEND_READY=1
    break
  fi
  sleep 2
done
if [[ "${BACKEND_READY}" -ne 1 ]]; then
  echo "STOP: backend readiness through the inference proxy failed." >&2
  tail -n 80 "${LOG_DIR}/backend.log" >&2
  exit 1
fi

echo "TaniAdaptif GPU stack ready at ${PUBLIC_API_BASE_URL}/api"
echo "Inference remains private on 127.0.0.1:5000. Logs: ${LOG_DIR}"

wait -n "${INFERENCE_PID}" "${BACKEND_PID}"
echo "STOP: one service exited; shutting down the stack." >&2
exit 1
