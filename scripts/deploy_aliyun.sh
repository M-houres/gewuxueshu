#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-M-houres}"
REPO_NAME="${REPO_NAME:-gewuxueshu}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/gewuxueshu}"
REPO_URL="${REPO_URL:-https://github.com/${REPO_OWNER}/${REPO_NAME}.git}"
TARBALL_URL="${TARBALL_URL:-https://codeload.github.com/${REPO_OWNER}/${REPO_NAME}/tar.gz/refs/heads/${BRANCH}}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/.env.prod}"
INITIAL_CREDITS_VALUE="${INITIAL_CREDITS_VALUE:-2000}"

# Network inside mainland often fails on DockerHub/GitHub. Keep mirrors on by default.
ENABLE_DOCKER_MIRROR="${ENABLE_DOCKER_MIRROR:-1}"
DOCKER_MIRRORS="${DOCKER_MIRRORS:-https://docker.m.daocloud.io,https://docker.1ms.run}"

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
  abort "请使用 root 运行，或先安装 sudo。"
fi

if ! command -v apt-get >/dev/null 2>&1; then
  abort "当前脚本仅支持 Ubuntu/Debian。"
fi

export DEBIAN_FRONTEND=noninteractive
log "安装基础依赖"
apt-get update -y
apt-get install -y ca-certificates curl tar git openssl docker.io docker-compose-plugin
systemctl enable --now docker

if [ "${ENABLE_DOCKER_MIRROR}" = "1" ]; then
  if [ ! -f /etc/docker/daemon.json ]; then
    log "配置 Docker 镜像加速"
    mkdir -p /etc/docker
    {
      echo "{"
      echo '  "registry-mirrors": ['
      first=1
      IFS=',' read -r -a mirrors <<<"${DOCKER_MIRRORS}"
      for mirror in "${mirrors[@]}"; do
        trimmed="$(echo "$mirror" | xargs)"
        [ -z "$trimmed" ] && continue
        if [ "$first" -eq 1 ]; then
          printf '    "%s"' "$trimmed"
          first=0
        else
          printf ',\n    "%s"' "$trimmed"
        fi
      done
      echo
      echo "  ]"
      echo "}"
    } >/etc/docker/daemon.json
    systemctl restart docker
  else
    log "检测到 /etc/docker/daemon.json 已存在，保持现有配置不覆盖"
  fi
fi

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
  local value="$2"
  local current
  current="$(read_env "$key" || true)"
  if [ -z "$current" ] || [[ "$current" == replace_with_* ]]; then
    set_env "$key" "$value"
  fi
}

fetch_repo() {
  local ok=""
  local parent_dir env_backup
  parent_dir="$(dirname "$APP_DIR")"
  mkdir -p "$parent_dir"

  env_backup=""
  if [ -f "$ENV_FILE" ]; then
    env_backup="/tmp/$(basename "$APP_DIR")-env-prod.backup.$$.tmp"
    cp "$ENV_FILE" "$env_backup"
  fi

  rm -rf "$APP_DIR"

  log "尝试 Git 拉取代码"
  for i in 1 2 3; do
    if git -c http.version=HTTP/1.1 clone -b "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"; then
      ok="1"
      break
    fi
    sleep 3
  done

  if [ -z "$ok" ]; then
    log "Git 失败，切换 codeload 压缩包方式"
    curl -fL --retry 8 --retry-all-errors "$TARBALL_URL" -o /tmp/${REPO_NAME}-${BRANCH}.tar.gz
    mkdir -p "$APP_DIR"
    tar -xzf /tmp/${REPO_NAME}-${BRANCH}.tar.gz -C "$APP_DIR" --strip-components=1
  fi

  [ -f "$APP_DIR/docker-compose.prod.yml" ] || abort "代码下载成功但缺少 docker-compose.prod.yml"
  [ -f "$APP_DIR/.env.prod.example" ] || abort "代码下载成功但缺少 .env.prod.example"

  if [ -n "$env_backup" ] && [ -f "$env_backup" ]; then
    cp "$env_backup" "$ENV_FILE"
  elif [ ! -f "$ENV_FILE" ]; then
    cp "$APP_DIR/.env.prod.example" "$ENV_FILE"
  fi
}

prepare_env() {
  log "准备生产环境变量"
  set_env "APP_ENV" "prod"
  set_env "INITIAL_CREDITS" "$INITIAL_CREDITS_VALUE"
  set_env "MYSQL_DATABASE" "$(read_env MYSQL_DATABASE || echo wuhongai)"

  ensure_secret "MYSQL_PASSWORD" "$(openssl rand -hex 16)"
  ensure_secret "JWT_SECRET" "$(openssl rand -hex 32)"
  ensure_secret "PAYMENT_SIGN_SECRET" "$(openssl rand -hex 32)"
  ensure_secret "ADMIN_INIT_PASSWORD" "$(openssl rand -base64 24 | tr -d '=+/' | cut -c1-18)"
}

deploy_stack() {
  log "启动容器"
  cd "$APP_DIR"
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" pull || true
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" up -d --build --remove-orphans
  docker compose --env-file "$ENV_FILE" -f "$APP_DIR/docker-compose.prod.yml" ps
}

health_check() {
  log "健康检查"
  for i in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1/health" >/dev/null 2>&1 || curl -fsS "http://127.0.0.1/api/v1/health" >/dev/null 2>&1; then
      echo "Health check passed."
      return 0
    fi
    sleep 2
  done
  echo "Warning: health check timed out. You can inspect logs with:"
  echo "docker compose --env-file $ENV_FILE -f $APP_DIR/docker-compose.prod.yml logs --tail=200"
}

fetch_repo
prepare_env
deploy_stack
health_check

log "部署完成"
echo "目录: $APP_DIR"
echo "环境文件: $ENV_FILE"
echo "请在阿里云安全组放行 80 端口（HTTPS 场景再放行 443）。"
