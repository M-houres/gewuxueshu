#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/M-houres/gewuxueshu.git}"
APP_DIR="${APP_DIR:-/opt/wuhongai}"
BRANCH="${BRANCH:-main}"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
elif command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  echo "Please run as root or install sudo first."
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  PKG_MGR="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MGR="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG_MGR="yum"
else
  echo "Unsupported Linux distribution."
  exit 1
fi

install_pkg() {
  case "$PKG_MGR" in
    apt)
      $SUDO apt-get update -y
      $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
      ;;
    dnf)
      $SUDO dnf install -y "$@"
      ;;
    yum)
      $SUDO yum install -y "$@"
      ;;
  esac
}

for c in curl git openssl; do
  if ! command -v "$c" >/dev/null 2>&1; then
    install_pkg "$c"
  fi
done

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO systemctl enable --now docker
fi

compose() {
  if $SUDO docker compose version >/dev/null 2>&1; then
    $SUDO docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    $SUDO docker-compose "$@"
  else
    install_pkg docker-compose-plugin || true
    if $SUDO docker compose version >/dev/null 2>&1; then
      $SUDO docker compose "$@"
    else
      echo "docker compose is unavailable."
      exit 1
    fi
  fi
}

$SUDO mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  $SUDO git clone -b "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
fi

$SUDO git -C "$APP_DIR" fetch origin "$BRANCH"
$SUDO git -C "$APP_DIR" checkout "$BRANCH"
$SUDO git -C "$APP_DIR" pull --ff-only origin "$BRANCH"

ENV_FILE="$APP_DIR/.env.prod"
if [ ! -f "$ENV_FILE" ]; then
  $SUDO cp "$APP_DIR/.env.prod.example" "$ENV_FILE"
fi

set_env() {
  local key="$1"
  local val="$2"
  local esc
  esc="$(printf '%s' "$val" | sed 's/[&|\\]/\\&/g')"
  if $SUDO grep -q "^${key}=" "$ENV_FILE"; then
    $SUDO sed -i "s|^${key}=.*|${key}=${esc}|" "$ENV_FILE"
  else
    printf "%s=%s\n" "$key" "$val" | $SUDO tee -a "$ENV_FILE" >/dev/null
  fi
}

read_env() {
  $SUDO awk -F= -v k="$1" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' "$ENV_FILE"
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

compose -f "$APP_DIR/docker-compose.prod.yml" up -d --build
compose -f "$APP_DIR/docker-compose.prod.yml" ps

echo "Done: $APP_DIR"
echo "Remember to open port 80 (and 443 for HTTPS) in Alibaba Cloud security group."
