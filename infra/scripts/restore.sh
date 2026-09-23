#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ $# -ne 2 || "$2" != "--confirm-replace" ]]; then
  printf 'Uso: %s RUTA_COPIA.tar.gz --confirm-replace\n' "$0" >&2
  printf 'La restauración reemplaza la base de datos y los archivos privados actuales.\n' >&2
  exit 2
fi

ARCHIVE="$(realpath -- "$1")"
require_file "${ARCHIVE}"
"${SCRIPT_DIR}/verify-backup.sh" "${ARCHIVE}"

STAGING="$(mktemp -d "${TMPDIR:-/tmp}/gesband-restore.XXXXXX")"
trap 'rm -rf -- "${STAGING}"' EXIT
tar -xzf "${ARCHIVE}" -C "${STAGING}"

compose stop web worker proxy
compose exec -T postgres sh -eu -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" dropdb --if-exists --force --username "$POSTGRES_USER" "$POSTGRES_DB" && PGPASSWORD="$POSTGRES_PASSWORD" createdb --username "$POSTGRES_USER" "$POSTGRES_DB"'
compose exec -T postgres sh -eu -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-owner --no-privileges' \
  < "${STAGING}/database.dump"

compose --profile tools run --rm -T maintenance \
  'find /data -mindepth 1 -delete; tar -C /data -xzf -' \
  < "${STAGING}/private-media.tar.gz"

compose up -d web worker proxy
compose exec -T web python manage.py check --deploy
printf 'Restauración completada y comprobación de Django superada.\n'

