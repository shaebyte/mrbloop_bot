#!/bin/bash
# Dumps the shared MySQL database to a timestamped, gzipped file and prunes
# dumps older than RETENTION_DAYS. Intended to be run on a schedule (cron on
# Linux, Task Scheduler on Windows) — this script itself does not schedule
# anything, it just performs one backup + prune cycle.
#
# Works two ways, auto-detected:
#   - direct: mysqldump connects straight to DB_HOST:DB_PORT (local/dev setup,
#     where MySQL's port is reachable from wherever this script runs).
#   - docker exec: production's docker-compose.prod.yml removes MySQL's port
#     mapping to the host on purpose (DB only reachable on the Docker
#     network), so this runs mysqldump *inside* the mysql container instead
#     and streams its output back out through gzip on the host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
RETENTION_DAYS=14
CONTAINER_NAME="${MYSQL_CONTAINER_NAME:-mrbloop_mysql}"

set -a
source "$ROOT_DIR/db.env"
set +a

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# --set-gtid-purged=OFF: the app DB user intentionally has no RELOAD privilege
# (least privilege, see 000_setup.sh), and without this flag mysqldump tries
# a FLUSH TABLES WITH READ LOCK for GTID state that fails and aborts the dump
# with only headers written — a "successful" empty backup.
DUMP_FLAGS=(--single-transaction --set-gtid-purged=OFF --routines --events)

# MYSQL_PWD instead of -p"$DB_PASSWORD": keeps the password out of the
# process list (`ps aux` / `docker top`), which -p on the command line does not.
if timeout 2 bash -c "cat < /dev/null > /dev/tcp/${DB_HOST:-localhost}/${DB_PORT:-3306}" 2>/dev/null; then
    echo "MySQL reachable directly at ${DB_HOST:-localhost}:${DB_PORT:-3306} — dumping straight from the host."
    MYSQL_PWD="$DB_PASSWORD" mysqldump -h "${DB_HOST:-localhost}" -P "${DB_PORT:-3306}" -u "$DB_USER" \
        "${DUMP_FLAGS[@]}" "$DB_NAME" | gzip > "$DUMP_FILE"
elif docker exec "$CONTAINER_NAME" true 2>/dev/null; then
    echo "MySQL port not reachable from here — dumping via 'docker exec $CONTAINER_NAME'."
    docker exec -e MYSQL_PWD="$DB_PASSWORD" "$CONTAINER_NAME" \
        mysqldump -u "$DB_USER" "${DUMP_FLAGS[@]}" "$DB_NAME" | gzip > "$DUMP_FILE"
else
    echo "ERROR: MySQL is reachable neither directly at ${DB_HOST:-localhost}:${DB_PORT:-3306} nor via 'docker exec $CONTAINER_NAME'." >&2
    echo "Set MYSQL_CONTAINER_NAME if your container has a different name." >&2
    exit 1
fi

echo "Backup written to $DUMP_FILE"

find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "Pruned backups older than ${RETENTION_DAYS} days."
