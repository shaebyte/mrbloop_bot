USE mrbloop_db;

-- Tracks which migration files (this one included) have already been
-- applied, so migrate.sh only re-applies what's new. Unprefixed: it's
-- infrastructure for the migrations process itself, not owned by any
-- one service.
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
