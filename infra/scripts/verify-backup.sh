#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ $# -ne 1 ]]; then
  printf 'Uso: %s RUTA_COPIA.tar.gz\n' "$0" >&2
  exit 2
fi

ARCHIVE="$(realpath -- "$1")"
require_file "${ARCHIVE}"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/gesband-verify.XXXXXX")"
trap 'rm -rf -- "${STAGING}"' EXIT

tar -tzf "${ARCHIVE}" | while IFS= read -r entry; do
  case "${entry}" in
    database.dump|private-media.tar.gz|SHA256SUMS|METADATA) ;;
    *) printf 'Entrada inesperada en la copia: %s\n' "${entry}" >&2; exit 1 ;;
  esac
done
tar -xzf "${ARCHIVE}" -C "${STAGING}"

(
  cd "${STAGING}"
  sha256sum --check SHA256SUMS
)
tar -tzf "${STAGING}/private-media.tar.gz" >/dev/null
compose exec -T postgres pg_restore --list < "${STAGING}/database.dump" >/dev/null

printf 'Copia válida: checksums, volcado PostgreSQL y archivo de medios correctos.\n'

