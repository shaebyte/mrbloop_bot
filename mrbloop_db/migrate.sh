#!/bin/bash
# Applies every migrations/*.sql file that isn't yet recorded in
# schema_migrations, in filename order, and records each one as it succeeds.
# Safe to re-run: already-applied files are skipped.
#
# Works two ways, auto-detected (same as backup.sh):
#   - direct: the `mysql` client on this host connects straight to
#     DB_HOST:DB_PORT (local/dev setup).
#   - docker exec: production runs everything in containers — MySQL's port
#     isn't published to the host and there's no `mysql` client installed on
#     the VPS host at all — so this runs `mysql` *inside* the mysql
#     container instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_NAME="${MYSQL_CONTAINER_NAME:-mrbloop_mysql}"

set -a
source "$ROOT_DIR/db.env"
set +a

USE_DOCKER=false
if command -v mysql >/dev/null 2>&1 && timeout 2 bash -c "cat < /dev/null > /dev/tcp/${DB_HOST:-localhost}/${DB_PORT:-3306}" 2>/dev/null; then
    echo "MySQL reachable directly at ${DB_HOST:-localhost}:${DB_PORT:-3306} — using the local mysql client."
    MYSQL_ARGS=(-h "${DB_HOST:-localhost}" -P "${DB_PORT:-3306}" -u "$DB_USER" "$DB_NAME")
elif docker exec "$CONTAINER_NAME" true 2>/dev/null; then
    echo "No local mysql client / DB not directly reachable — using 'docker exec $CONTAINER_NAME'."
    USE_DOCKER=true
    MYSQL_ARGS=(-u "$DB_USER" "$DB_NAME")
else
    echo "ERROR: MySQL is reachable neither directly nor via 'docker exec $CONTAINER_NAME'." >&2
    echo "Set MYSQL_CONTAINER_NAME if your container has a different name." >&2
    exit 1
fi

# MYSQL_PWD instead of -p"$DB_PASSWORD": keeps the password out of the
# process list (`ps aux` / `docker top`).
run_mysql() {
    if [ "$USE_DOCKER" = true ]; then
        docker exec -i -e MYSQL_PWD="$DB_PASSWORD" "$CONTAINER_NAME" mysql "${MYSQL_ARGS[@]}" "$@"
    else
        MYSQL_PWD="$DB_PASSWORD" mysql "${MYSQL_ARGS[@]}" "$@"
    fi
}

# Bootstrap: create the tracking table if this is the very first run, before
# 005_schema_migrations.sql itself has had a chance to be applied.
run_mysql -e "
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"

for file in "$MIGRATIONS_DIR"/*.sql; do
    name="$(basename "$file")"
    already_applied="$(run_mysql -N -s -e "SELECT COUNT(*) FROM schema_migrations WHERE filename = '${name}';")"

    if [ "$already_applied" -eq 0 ]; then
        echo "Applying $name..."
        run_mysql < "$file"
        run_mysql -e "INSERT INTO schema_migrations (filename) VALUES ('${name}');"
    else
        echo "Skipping $name (already applied)"
    fi
done

echo "Done."
