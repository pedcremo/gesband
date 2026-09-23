#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

BACKUP_DIR="${1:-${INFRA_DIR}/backups}"
STAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
ARCHIVE="${BACKUP_DIR}/gesband-${STAMP}.tar.gz"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/gesband-backup.XXXXXX")"
trap 'rm -rf -- "${STAGING}"' EXIT

mkdir -p "${BACKUP_DIR}"
umask 077

compose exec -T postgres sh -eu -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "${STAGING}/database.dump"

compose --profile tools run --rm -T maintenance \
  'tar -C /data -czf - .' > "${STAGING}/private-media.tar.gz"

(
  cd "${STAGING}"
  sha256sum database.dump private-media.tar.gz > SHA256SUMS
  printf 'created_at=%s\nformat_version=1\n' "${STAMP}" > METADATA
  tar -czf "${ARCHIVE}" database.dump private-media.tar.gz SHA256SUMS METADATA
)

printf 'Copia creada: %s\n' "${ARCHIVE}"
"${SCRIPT_DIR}/verify-backup.sh" "${ARCHIVE}"

