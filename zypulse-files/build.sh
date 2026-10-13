#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# ZyPulse - Render build script (single Web Service, Free plan)
#
# 1. Install Python dependencies for the FastAPI backend.
# 2. Make sure Node.js and pnpm are available.
# 3. Build the React/Vite frontend into frontend/dist.
#
# The FastAPI app serves frontend/dist, so everything runs on ONE service.
# ---------------------------------------------------------------------------
set -o errexit
set -o nounset
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> [1/3] Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

echo "==> [2/3] Preparing Node.js and pnpm"
# On Render, set NODE_VERSION (for example 22) so the Node toolchain exists.
export NODE_VERSION="${NODE_VERSION:-22}"
echo "    NODE_VERSION=${NODE_VERSION}"
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node not found. Add NODE_VERSION=22 to the Render environment." >&2
  exit 1
fi
echo "    node $(node --version)"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "    pnpm not found - trying corepack"
  corepack enable >/dev/null 2>&1 || true
  corepack prepare pnpm@10 --activate >/dev/null 2>&1 || true
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "    corepack unavailable - installing pnpm with npm"
  npm install -g pnpm@10
fi
echo "    pnpm $(pnpm --version)"

echo "==> [3/3] Building the React/Vite frontend"
cd "$ROOT_DIR/frontend"
pnpm install --frozen-lockfile
pnpm run build

cd "$ROOT_DIR"
echo "==> Build complete. Frontend output: frontend/dist"
