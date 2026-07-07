#!/bin/bash
# Applies every migrations/*.sql file that isn't yet recorded in
# schema_migrations, in filename order, and records each one as it succeeds.
# Safe to re-run: already-applied files are skipped.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

set -a
source "$ROOT_DIR/db.env"
set +a

MYSQL_ARGS=(-h "${DB_HOST:-localhost}" -P "${DB_PORT:-3306}" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME")

# Bootstrap: create the tracking table if this is the very first run, before
# 005_schema_migrations.sql itself has had a chance to be applied.
mysql "${MYSQL_ARGS[@]}" -e "
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"

for file in "$MIGRATIONS_DIR"/*.sql; do
    name="$(basename "$file")"
    already_applied="$(mysql "${MYSQL_ARGS[@]}" -N -s -e "SELECT COUNT(*) FROM schema_migrations WHERE filename = '${name}';")"

    if [ "$already_applied" -eq 0 ]; then
        echo "Applying $name..."
        mysql "${MYSQL_ARGS[@]}" < "$file"
        mysql "${MYSQL_ARGS[@]}" -e "INSERT INTO schema_migrations (filename) VALUES ('${name}');"
    else
        echo "Skipping $name (already applied)"
    fi
done

echo "Done."
