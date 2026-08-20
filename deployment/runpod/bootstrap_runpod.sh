#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/workspace/TaniAdaptif}"

if [[ ! -f "${REPO_ROOT}/inference_api/requirements-diffusers.txt" ]]; then
  echo "STOP: repository not found at ${REPO_ROOT}." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends curl nodejs npm
  rm -rf /var/lib/apt/lists/*
fi

NODE_MAJOR="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
if [[ "${NODE_MAJOR}" -lt 18 ]]; then
  echo "STOP: Node.js 18 or newer is required; found $(node --version)." >&2
  exit 1
fi

cd "${REPO_ROOT}"
python -m pip install --no-cache-dir --upgrade pip setuptools wheel
python -m pip install --no-cache-dir -r inference_api/requirements-diffusers.txt
npm --prefix backend-nodejs ci --omit=dev

mkdir -p /workspace/taniadaptif-data/generated
mkdir -p /workspace/taniadaptif-evidence
mkdir -p /workspace/taniadaptif-logs
mkdir -p /workspace/huggingface
mkdir -p /workspace/taniadaptif-secrets

python -m compileall -q inference_api
node --check backend-nodejs/src/app.js
node --check backend-nodejs/src/routes/visualRoutes.js
node --check backend-nodejs/src/services/inferenceService.js

echo "Bootstrap complete. Create /workspace/taniadaptif-secrets/runtime.env, then run deployment/runpod/start_stack.sh."
