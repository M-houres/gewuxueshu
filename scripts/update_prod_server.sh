#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-M-houres}"
REPO_NAME="${REPO_NAME:-gewuxueshu}"
BRANCH="${BRANCH:-main}"

APP_DIR="${APP_DIR:-/opt/gewuxueshu}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-${APP_DIR}/docker-compose.prod.yml}"
FRONTEND_BIND="${FRONTEND_BIND:-127.0.0.1:8080:80}"
KEEP_ENV="${KEEP_ENV:-1}"

TARBALL_URL="${TARBALL_URL:-https://codeload.github.com/${REPO_OWNER}/${REPO_NAME}/tar.gz/refs/heads/${BRANCH}}"
TMP_ROOT="$(mktemp -d /tmp/gewu-update.XXXXXX)"

log() {
  printf "\n[%s] %s\n" "$(date '+%F %T')" "$*"
}

abort() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  rm -rf "${TMP_ROOT}"
}
trap cleanup EXIT

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || abort "Missing command: $1"
}

validate_paths() {
  [ -n "${APP_DIR}" ] || abort "APP_DIR is empty"
  [ "${APP_DIR}" != "/" ] || abort "APP_DIR cannot be /"
  case "${APP_DIR}" in
    /opt/*) ;;
    *)
      abort "APP_DIR must be under /opt for safety. Current: ${APP_DIR}"
      ;;
  esac
}

download_source() {
  local tarball="${TMP_ROOT}/source.tar.gz"
  log "Downloading source from ${TARBALL_URL}"
  curl -fL --retry 8 --retry-delay 2 --retry-all-errors "${TARBALL_URL}" -o "${tarball}"
  tar -xzf "${tarball}" -C "${TMP_ROOT}"
}

sync_source() {
  local src_dir
  src_dir="$(find "${TMP_ROOT}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "${src_dir}" ] || abort "Cannot locate extracted source directory"
  [ -f "${src_dir}/docker-compose.prod.yml" ] || abort "Invalid source: missing docker-compose.prod.yml"
  [ -f "${src_dir}/.env.prod.example" ] || abort "Invalid source: missing .env.prod.example"

  if [ "${KEEP_ENV}" = "1" ] && [ -f "${ENV_FILE}" ]; then
    cp "${ENV_FILE}" "${TMP_ROOT}/.env.prod.keep"
  fi

  log "Sync source into ${APP_DIR}"
  run_root mkdir -p "${APP_DIR}"

  if command -v rsync >/dev/null 2>&1; then
    run_root rsync -a --delete \
      --exclude ".env.prod" \
      --exclude ".env" \
      "${src_dir}/" "${APP_DIR}/"
  else
    validate_paths
    run_root rm -rf "${APP_DIR}"
    run_root mkdir -p "${APP_DIR}"
    run_root cp -a "${src_dir}/." "${APP_DIR}/"
  fi

  if [ "${KEEP_ENV}" = "1" ] && [ -f "${TMP_ROOT}/.env.prod.keep" ]; then
    run_root cp "${TMP_ROOT}/.env.prod.keep" "${ENV_FILE}"
  elif [ ! -f "${ENV_FILE}" ] && [ -f "${APP_DIR}/.env.prod.example" ]; then
    run_root cp "${APP_DIR}/.env.prod.example" "${ENV_FILE}"
  fi
}

patch_compose_for_host_nginx() {
  [ -f "${COMPOSE_FILE}" ] || abort "Compose file not found: ${COMPOSE_FILE}"
  local escaped_bind
  escaped_bind="$(printf '%s' "${FRONTEND_BIND}" | sed 's/[\/&]/\\&/g')"
  run_root sed -i "s#\"80:80\"#\"${escaped_bind}\"#g" "${COMPOSE_FILE}"
}

deploy_compose() {
  log "Deploying containers"
  cd "${APP_DIR}"
  run_root docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build --remove-orphans
  run_root docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
}

health_check() {
  log "Health check"
  local i services
  for i in $(seq 1 40); do
    services="$(run_root docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps --status running --services || true)"
    if \
      echo "${services}" | grep -qx "backend" && \
      echo "${services}" | grep -qx "frontend" && \
      echo "${services}" | grep -qx "worker"
    then
      echo "Health check passed."
      return 0
    fi
    sleep 2
  done
  echo "WARNING: health check timeout."
  echo "Run: sudo docker compose --env-file ${ENV_FILE} -f ${COMPOSE_FILE} logs --tail=200"
  return 1
}

main() {
  require_cmd curl
  require_cmd tar
  require_cmd docker
  validate_paths
  download_source
  sync_source
  patch_compose_for_host_nginx
  deploy_compose
  health_check
  log "Update complete"
  echo "App dir: ${APP_DIR}"
  echo "Branch: ${BRANCH}"
}

main "$@"
