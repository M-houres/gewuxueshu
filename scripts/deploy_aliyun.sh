#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-M-houres}"
REPO_NAME="${REPO_NAME:-gewuxueshu}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/gewuxueshu}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}_prev}"

REPO_URL="${REPO_URL:-https://github.com/${REPO_OWNER}/${REPO_NAME}.git}"
TARBALL_URL="${TARBALL_URL:-https://codeload.github.com/${REPO_OWNER}/${REPO_NAME}/tar.gz/refs/heads/${BRANCH}}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/.env.prod}"
INITIAL_CREDITS_VALUE="${INITIAL_CREDITS_VALUE:-2000}"

# For mainland network environments.
ENABLE_DOCKER_MIRROR="${ENABLE_DOCKER_MIRROR:-1}"
DOCKER_MIRRORS="${DOCKER_MIRRORS:-https://docker.m.daocloud.io,https://docker.1ms.run}"

log() {
  printf "\n[%s] %s\n" "$(date '+%H:%M:%S')" "$*"
}

abort() {
  echo "ERROR: $*" >&2
  exit 1
}

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
      exec sudo -E bash "$0" "$@"
    fi
    abort "Please run as root or install sudo."
  fi
}

install_dependencies() {
  command -v apt-get >/dev/null 2>&1 || abort "Only Ubuntu/Debian are supported."

  export DEBIAN_FRONTEND=noninteractive
  log "Install dependencies"
  apt-get update -y
  apt-get install -y ca-certificates curl tar git openssl docker.io docker-compose-plugin
  systemctl enable --now docker
}

configure_docker_mirror() {
  if [ "${ENABLE_DOCKER_MIRROR}" != "1" ]; then
    return
  fi

  if [ -f /etc/docker/daemon.json ]; then
    log "Keep existing /etc/docker/daemon.json"
    return
  fi

  log "Configure docker registry mirrors"
  mkdir -p /etc/docker
  {
    echo "{"
    echo '  "registry-mirrors": ['
    first=1
    IFS=',' read -r -a mirrors <<<"${DOCKER_MIRRORS}"
    for mirror in "${mirrors[@]}"; do
      m="$(echo "$mirror" | xargs)"
      [ -z "$m" ] && continue
      if [ "$first" -eq 1 ]; then
        printf '    "%s"' "$m"
        first=0
      else
        printf ',\n    "%s"' "$m"
      fi
    done
    echo
    echo "  ]"
    echo "}"
  } >/etc/docker/daemon.json
  systemctl restart docker
}

set_env() {
  local key="$1"
  local val="$2"
  local esc
  esc="$(printf '%s' "$val" | sed 's/[&|\\]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${esc}|" "$ENV_FILE"
  else
    printf "%s=%s\n" "$key" "$val" >>"$ENV_FILE"
  fi
}

read_env() {
  awk -F= -v k="$1" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' "$ENV_FILE"
}

ensure_secret() {
  local key="$1"
  local val="$2"
  local current
  current="$(read_env "$key" || true)"
  if [ -z "$current" ] || [[ "$current" == replace_with_* ]]; then
    set_env "$key" "$val"
  fi
}

fetch_repo() {
  local ok=""
  local parent_dir env_backup tmp_tar
  parent_dir="$(dirname "$APP_DIR")"
  mkdir -p "$parent_dir"

  env_backup=""
  if [ -f "$ENV_FILE" ]; then
    env_backup="/tmp/$(basename "$APP_DIR")-env-prod.backup.$$.tmp"
    cp "$ENV_FILE" "$env_backup"
  fi

  if [ -d "$APP_DIR" ]; then
    rm -rf "$BACKUP_DIR"
    mv "$APP_DIR" "$BACKUP_DIR"
  fi

  log "Download source: git clone"
  for i in 1 2 3; do
    if git -c http.version=HTTP/1.1 clone -b "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"; then
      ok="1"
      break
    fi
    sleep 3
  done

  if [ -z "$ok" ]; then
    log "Git failed, fallback to codeload tarball"
    tmp_tar="/tmp/${REPO_NAME}-${BRANCH}.tar.gz"
    curl -fL --retry 8 --retry-all-errors "$TARBALL_URL" -o "$tmp_tar"
    mkdir -p "$APP_DIR"
    tar -xzf "$tmp_tar" -C "$APP_DIR" --strip-components=1
  fi

  [ -f "$APP_DIR/docker-compose.prod.yml" ] || abort "Missing docker-compose.prod.yml"
  [ -f "$APP_DIR/.env.prod.example" ] || abort "Missing .env.prod.example"

  if [ -n "$env_backup" ] && [ -f "$env_backup" ]; then
    cp "$env_backup" "$ENV_FILE"
  elif [ ! -f "$ENV_FILE" ]; then
    cp "$APP_DIR/.env.prod.example" "$ENV_FILE"
  fi
}

prepare_env() {
  log "Prepare .env.prod"
  set_env "APP_ENV" "prod"
  set_env "INITIAL_CREDITS" "$INITIAL_CREDITS_VALUE"
  set_env "MYSQL_DATABASE" "$(read_env MYSQL_DATABASE || echo wuhongai)"

  ensure_secret "MYSQL_PASSWORD" "$(openssl rand -hex 16)"
  ensure_secret "JWT_SECRET" "$(openssl rand -hex 32)"
  ensure_secret "PAYMENT_SIGN_SECRET" "$(openssl rand -hex 32)"
  ensure_secret "ADMIN_INIT_PASSWORD" "$(openssl rand -base64 24 | tr -d '=+/' | cut -c1-18)"
}

deploy_stack() {
  log "Start containers"
  cd "$APP_DIR"
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" pull || true
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" up -d --build --remove-orphans
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" ps
}

health_check() {
  log "Health check"
  for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1/health" >/dev/null 2>&1 || curl -fsS "http://127.0.0.1/api/v1/health" >/dev/null 2>&1; then
      echo "Health check passed."
      return 0
    fi
    sleep 2
  done
  echo "WARNING: health check timeout."
  echo "Inspect logs:"
  echo "docker compose --env-file $ENV_FILE -f $APP_DIR/docker-compose.prod.yml logs --tail=200"
}

main() {
  require_root "$@"
  install_dependencies
  configure_docker_mirror
  fetch_repo
  prepare_env
  deploy_stack
  health_check

  log "Deploy done"
  echo "App dir: $APP_DIR"
  echo "Backup dir: $BACKUP_DIR"
  echo "Env file: $ENV_FILE"
  echo "Open port 80 (and 443 if using HTTPS) in Aliyun security group."
  echo "Rollback command: bash $APP_DIR/scripts/deploy_aliyun_rollback.sh"
}

main "$@"
