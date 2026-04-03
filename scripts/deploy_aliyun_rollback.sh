#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/gewuxueshu}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}_prev}"
FAILED_DIR="${FAILED_DIR:-${APP_DIR}_failed_$(date +%Y%m%d_%H%M%S)}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/.env.prod}"

log() {
  printf "\n[%s] %s\n" "$(date '+%H:%M:%S')" "$*"
}

abort() {
  echo "ERROR: $*" >&2
  exit 1
}

if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  abort "Please run as root or install sudo."
fi

[ -d "$BACKUP_DIR" ] || abort "Backup directory not found: $BACKUP_DIR"
[ -f "$BACKUP_DIR/docker-compose.prod.yml" ] || abort "Backup missing docker-compose.prod.yml"

if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/docker-compose.prod.yml" ]; then
  log "Stop current containers"
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" down || true
fi

if [ -d "$APP_DIR" ]; then
  log "Move current app to failed snapshot: $FAILED_DIR"
  mv "$APP_DIR" "$FAILED_DIR"
fi

log "Restore backup to app dir"
mv "$BACKUP_DIR" "$APP_DIR"

if [ ! -f "$APP_DIR/.env.prod" ] && [ -f "$FAILED_DIR/.env.prod" ]; then
  cp "$FAILED_DIR/.env.prod" "$APP_DIR/.env.prod"
fi

ENV_FILE="${APP_DIR}/.env.prod"
[ -f "$ENV_FILE" ] || cp "$APP_DIR/.env.prod.example" "$ENV_FILE"

log "Start restored version"
docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" up -d --build --remove-orphans
docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" ps

log "Rollback done"
echo "Current dir: $APP_DIR"
echo "Failed snapshot: $FAILED_DIR"
