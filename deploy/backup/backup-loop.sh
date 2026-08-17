#!/bin/sh
# Sleeps until the configured local time, dumps, repeats. TZ is set on the
# service, so BACKUP_HOUR means local time.
set -eu

# `date +%H` yields "08"/"09", which POSIX arithmetic reads as octal and treats
# as a syntax error — the loop would die every morning between 08:00 and 09:59.
strip_leading_zero() {
    value="${1#0}"
    echo "${value:-0}"
}

while :; do
    hour=$(strip_leading_zero "$(date +%H)")
    minute=$(strip_leading_zero "$(date +%M)")
    second=$(strip_leading_zero "$(date +%S)")
    now=$((hour * 3600 + minute * 60 + second))

    target=$(( $(strip_leading_zero "${BACKUP_HOUR:-3}") * 3600 \
             + $(strip_leading_zero "${BACKUP_MINUTE:-15}") * 60 ))

    delta=$((target - now))
    [ "$delta" -le 0 ] && delta=$((delta + 86400))

    echo "[backup] next run in ${delta}s"
    sleep "$delta"

    # Never exit the loop on a failed dump: tomorrow's attempt should still run.
    /bin/sh /opt/backup/run-backup.sh || echo "[backup] run failed; retrying tomorrow" >&2
done
