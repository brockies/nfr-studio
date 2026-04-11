#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "NFR Studio demo runner"
echo "Repo: $ROOT_DIR"

if [[ ! -d "venv" ]]; then
  echo "Creating venv..."
  python3 -m venv venv
fi

source venv/bin/activate

python - <<'PY' || {
  echo "Installing backend dependencies..."
  python -m pip install -r backend/requirements.txt
}
import fastapi, uvicorn  # noqa: F401
import chromadb  # noqa: F401
import tiktoken  # noqa: F401
print("Python deps OK")
PY

if [[ -f ".env" ]]; then
  if ! rg -n "^OPENAI_API_KEY=" .env >/dev/null 2>&1; then
    echo "Warning: .env exists but OPENAI_API_KEY is missing."
  fi
else
  echo "Warning: .env not found (OPENAI_API_KEY is required to run the pipeline)."
fi

python - <<'PY' || true
from chromadb import PersistentClient

c = PersistentClient(path=".chroma")
try:
    col = c.get_collection("nfr_kb")
    print(f"KB: collection=nfr_kb chunks={col.count()}")
except Exception:
    print("KB: collection nfr_kb not found yet (ingest via `python scripts/ingest_knowledge_base.py`).")
PY

if [[ ! -d "frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

backend_pid=""
frontend_pid=""

cleanup() {
  set +e
  if [[ -n "${frontend_pid}" ]]; then kill "${frontend_pid}" 2>/dev/null || true; fi
  if [[ -n "${backend_pid}" ]]; then kill "${backend_pid}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:${BACKEND_PORT} ..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" > /tmp/nfr_studio_backend.log 2>&1 &
backend_pid="$!"

echo "Starting frontend on http://localhost:${FRONTEND_PORT} ..."
(cd frontend && npm run dev -- --host 127.0.0.1 --port "${FRONTEND_PORT}") > /tmp/nfr_studio_frontend.log 2>&1 &
frontend_pid="$!"

echo ""
echo "Demo is starting:"
echo "- Frontend: http://localhost:${FRONTEND_PORT}"
echo "- Backend:  http://localhost:${BACKEND_PORT} (health: /api/health)"
echo ""
echo "Logs:"
echo "- Backend:  /tmp/nfr_studio_backend.log"
echo "- Frontend: /tmp/nfr_studio_frontend.log"
echo ""
echo "Press Ctrl+C to stop."

wait

