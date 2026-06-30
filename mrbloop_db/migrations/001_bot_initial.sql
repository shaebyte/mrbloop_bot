-- ============================================================
-- Migration 001: mrbloop_bot schema – initial tables
-- Run as root:
--   mysql -u root -p < migrations/001_bot_initial.sql
-- ============================================================

USE mrbloop_db;

-- Servers that use the bot
CREATE TABLE IF NOT EXISTS dbot_guilds (
    guild_id            BIGINT UNSIGNED  NOT NULL,
    guild_name          VARCHAR(100)     NOT NULL,
    birthday_channel_id BIGINT UNSIGNED  NULL DEFAULT NULL,
    event_channel_id    BIGINT UNSIGNED  NULL DEFAULT NULL,
    joined_at           DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Birthdays
-- Storage strategy:
--   birth_month + birth_day : day/month only, no year (privacy)
--   region                  : AMERICAS | EMEA | APAC (determines when the congratulation is sent)
--   last_greeted_year       : prevents duplicate congratulations in the same year
CREATE TABLE IF NOT EXISTS dbot_user_birthdays (
    id                BIGINT UNSIGNED              NOT NULL AUTO_INCREMENT,
    user_id           BIGINT UNSIGNED              NOT NULL,
    guild_id          BIGINT UNSIGNED              NOT NULL,
    birth_month       TINYINT UNSIGNED             NOT NULL,   -- 1-12
    birth_day         TINYINT UNSIGNED             NOT NULL,   -- 1-31
    region            ENUM('AMERICAS','EMEA','APAC') NOT NULL DEFAULT 'EMEA',
    last_greeted_year YEAR                         NULL DEFAULT NULL,
    created_at        DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_guild (user_id, guild_id),
    INDEX idx_birthday (birth_month, birth_day),
    INDEX idx_guild    (guild_id),
    CONSTRAINT fk_birthday_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Events (feature 2 – placeholder)
CREATE TABLE IF NOT EXISTS dbot_events (
    id              BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    guild_id        BIGINT UNSIGNED  NOT NULL,
    created_by      BIGINT UNSIGNED  NOT NULL,
    title           VARCHAR(200)     NOT NULL,
    description     TEXT             NULL,
    event_datetime  DATETIME         NOT NULL,
    timezone        VARCHAR(64)      NOT NULL DEFAULT 'UTC',
    channel_id      BIGINT UNSIGNED  NULL,
    reminder_sent   BOOLEAN          NOT NULL DEFAULT 0,
    created_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_guild_event (guild_id, event_datetime),
    CONSTRAINT fk_event_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -- Giftcodes (feature 3 – placeholder)
-- CREATE TABLE IF NOT EXISTS dbot_giftcodes (
--     id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
--     code        VARCHAR(100)     NOT NULL,
--     guild_id    BIGINT UNSIGNED  NULL,
--     created_by  BIGINT UNSIGNED  NOT NULL,
--     max_uses    INT UNSIGNED     NULL DEFAULT NULL,
--     uses_count  INT UNSIGNED     NOT NULL DEFAULT 0,
--     expires_at  DATETIME         NULL DEFAULT NULL,
--     reward_data JSON             NULL,
--     is_active   BOOLEAN          NOT NULL DEFAULT 1,
--     created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     PRIMARY KEY (id),
--     UNIQUE KEY uq_code (code),
--     INDEX idx_guild_active (guild_id, is_active)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- CREATE TABLE IF NOT EXISTS dbot_giftcode_redemptions (
--     id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
--     code_id     BIGINT UNSIGNED  NOT NULL,
--     user_id     BIGINT UNSIGNED  NOT NULL,
--     guild_id    BIGINT UNSIGNED  NOT NULL,
--     redeemed_at DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     PRIMARY KEY (id),
--     UNIQUE KEY uq_user_code (user_id, code_id),
--     CONSTRAINT fk_redemption_code FOREIGN KEY (code_id) REFERENCES giftcodes (id) ON DELETE CASCADE,
--     INDEX idx_code (code_id)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;