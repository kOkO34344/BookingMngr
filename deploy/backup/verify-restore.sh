#!/bin/sh
# Restore drill: proves a dump is usable, without touching the live database.
# Run from the repo root on the host:
#   ./deploy/backup/verify-restore.sh backups/bookingmngr-20260817-031500.dump
#
# An untested backup is not a backup. Run this the day you deploy, then monthly.
set -eu

dump="${1:?usage: verify-restore.sh <path-to-dump>}"
[ -f "$dump" ] || { echo "No such dump: $dump" >&2; exit 1; }

scratch="restore_check_$(date +%s)"
compose="docker compose"
psql_user="${POSTGRES_USER:-bookingmngr}"

cleanup() {
    $compose exec -T db dropdb -U "$psql_user" --if-exists "$scratch" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Restoring $dump into scratch database $scratch ..."
$compose exec -T db createdb -U "$psql_user" "$scratch"
$compose exec -T db pg_restore -U "$psql_user" -d "$scratch" --no-owner < "$dump"

echo
echo "Row counts in the restored copy:"
$compose exec -T db psql -U "$psql_user" -d "$scratch" -c \
    "SELECT (SELECT count(*) FROM reservations) AS reservations,
            (SELECT count(*) FROM properties)   AS properties,
            (SELECT count(*) FROM units)        AS units,
            (SELECT count(*) FROM tasks)        AS tasks,
            (SELECT count(*) FROM users)        AS users,
            (SELECT max(version_num) FROM alembic_version) AS schema;"

echo "Same query against the live database, for comparison:"
$compose exec -T db psql -U "$psql_user" -d "${POSTGRES_DB:-bookingmngr}" -c \
    "SELECT (SELECT count(*) FROM reservations) AS reservations,
            (SELECT count(*) FROM properties)   AS properties,
            (SELECT count(*) FROM units)        AS units,
            (SELECT count(*) FROM tasks)        AS tasks,
            (SELECT count(*) FROM users)        AS users,
            (SELECT max(version_num) FROM alembic_version) AS schema;"

echo
echo "Drill passed. Scratch database dropped."
