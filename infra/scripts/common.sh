#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${INFRA_DIR}/compose.yaml"

compose() {
  local args=(-f "${COMPOSE_FILE}")
  if [[ -f "${INFRA_DIR}/.env" ]]; then
    args=(--env-file "${INFRA_DIR}/.env" "${args[@]}")
  fi
  docker compose "${args[@]}" "$@"
}

require_file() {
  local path="$1"
  if [[ ! -f "${path}" ]]; then
    printf 'No existe el archivo requerido: %s\n' "${path}" >&2
    exit 1
  fi
}

