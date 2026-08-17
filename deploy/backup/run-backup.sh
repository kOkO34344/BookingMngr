#!/bin/sh
# One dump. Also runnable on demand:
#   docker compose exec backup /bin/sh /opt/backup/run-backup.sh
# Take one before any deploy that carries a migration.
set -eu

stamp=$(date +%Y%m%d-%H%M%S)
out="/backups/bookingmngr-${stamp}.dump"

echo "[backup] $(date -Iseconds) starting ${out}"

# Write to .tmp first so an interrupted dump is never mistaken for a good one.
if ! pg_dump --format=custom --compress=9 --file="${out}.tmp"; then
    echo "[backup] FAILED: pg_dump exited non-zero" >&2
    rm -f "${out}.tmp"
    exit 1
fi
mv "${out}.tmp" "${out}"

# A dump pg_restore cannot even read is not a backup. Cheap to check, and it
# catches truncation and disk-full long before the day you actually need it.
if ! pg_restore --list "${out}" >/dev/null 2>&1; then
    echo "[backup] FAILED: ${out} is not a readable custom-format dump" >&2
    exit 1
fi

chmod 600 "${out}"
echo "[backup] ok $(du -h "${out}" | cut -f1) ${out}"

find /backups -maxdepth 1 -name 'bookingmngr-*.dump' -mtime "+${RETENTION_DAYS:-14}" -print -delete
find /backups -maxdepth 1 -name 'bookingmngr-*.dump.tmp' -mmin +120 -delete

echo "[backup] dumps retained: $(find /backups -maxdepth 1 -name 'bookingmngr-*.dump' | wc -l | tr -d ' ')"
