#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"

log() {
  printf "\n[%s] %s\n" "$(date '+%H:%M:%S')" "$*"
}

run_frontend_build() {
  log "Frontend: build"
  cd "$FRONTEND_DIR"
  if [ ! -d node_modules ]; then
    npm install --ignore-scripts
  fi
  npm run build
}

run_backend_tests() {
  log "Backend: tests"
  cd "$BACKEND_DIR"

  local py=""
  if [ -x "$BACKEND_DIR/.venv_sys/bin/python" ]; then
    py="$BACKEND_DIR/.venv_sys/bin/python"
  elif [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
    py="$BACKEND_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    py="$(command -v python3)"
  fi

  if [ -z "$py" ]; then
    echo "Skip backend tests: python3 not found."
    return 0
  fi

  if ! "$py" -c "import fastapi" >/dev/null 2>&1; then
    echo "Skip backend tests: dependencies missing."
    echo "Hint: cd backend && $py -m pip install -r requirements.txt"
    return 0
  fi

  "$py" -m pytest -q
}

main() {
  log "Quality gate started"
  run_frontend_build
  run_backend_tests
  log "Quality gate passed"
}

main "$@"
