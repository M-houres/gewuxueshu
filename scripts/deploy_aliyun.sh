#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/M-houres/gewuxueshu.git}"
APP_DIR="${APP_DIR:-/opt/gewuxueshu}"
BRANCH="${BRANCH:-main}"

if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  echo "Please run as root or install sudo first."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script currently supports Ubuntu/Debian only."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git openssl docker.io docker-compose-plugin
systemctl enable --now docker

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker install failed."
  exit 1
fi

mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  git -c http.version=HTTP/1.1 clone -b "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
fi

git -C "$APP_DIR" fetch origin "$BRANCH"
git -C "$APP_DIR" checkout "$BRANCH"
git -C "$APP_DIR" pull --ff-only origin "$BRANCH"

ENV_FILE="$APP_DIR/.env.prod"
if [ ! -f "$ENV_FILE" ]; then
  cp "$APP_DIR/.env.prod.example" "$ENV_FILE"
fi

set_env() {
  local key="$1"
  local val="$2"
  local esc
  esc="$(printf '%s' "$val" | sed 's/[&|\\]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${esc}|" "$ENV_FILE"
  else
    printf "%s=%s\n" "$key" "$val" >> "$ENV_FILE"
  fi
}

read_env() {
  awk -F= -v k="$1" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' "$ENV_FILE"
}

ensure_secret() {
  local key="$1"
  local value="$2"
  local current
  current="$(read_env "$key" || true)"
  if [ -z "$current" ] || [[ "$current" == replace_with_* ]]; then
    set_env "$key" "$value"
  fi
}

ensure_secret "MYSQL_PASSWORD" "$(openssl rand -hex 16)"
ensure_secret "JWT_SECRET" "$(openssl rand -hex 32)"
ensure_secret "PAYMENT_SIGN_SECRET" "$(openssl rand -hex 32)"
ensure_secret "ADMIN_INIT_PASSWORD" "$(openssl rand -base64 18 | tr -d '=+/' | cut -c1-16)"
set_env "APP_ENV" "prod"
set_env "INITIAL_CREDITS" "2000"

cd "$APP_DIR"
docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" up -d --build
docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" ps

echo "Done: $APP_DIR"
echo "Open port 80 in Alibaba Cloud security group (443 for HTTPS)."
