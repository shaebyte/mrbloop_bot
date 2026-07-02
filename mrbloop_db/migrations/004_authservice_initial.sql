USE mrbloop_db;

-- Cross-cutting table, intentionally unprefixed: owned by authservice but
-- consumed (via JWT verification only, never direct queries) by
-- autoredeemgifts_v5 and alliancemanagement too.
CREATE TABLE IF NOT EXISTS auth_users (
    id INT AUTO_INCREMENT NOT NULL,
    username VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'alliance') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_auth_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
