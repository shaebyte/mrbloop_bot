-- ============================================================
-- Migration 001: mrbloop_bot schema — feature-framework design
-- Run as root:
--   mysql -u root -p < migrations/001_bot_initial.sql
-- ============================================================

USE mrbloop_db;

-- Servers that use the bot — core identity only.
-- is_active: the guild row stays around after the bot is kicked instead of being
-- hard-deleted, so guild config (settings/features) doesn't accidentally cascade
-- away. Personal data is cleaned up via a separate job after a grace period,
-- not implicitly through this row.
CREATE TABLE IF NOT EXISTS dbot_guilds (
    guild_id    BIGINT UNSIGNED  NOT NULL,
    guild_name  VARCHAR(100)     NOT NULL,
    is_active   BOOLEAN          NOT NULL DEFAULT 1,
    joined_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Feature catalog. Adding a new feature = one row here, no new migration for a
-- toggle table. is_globally_enabled allows staged rollout (the feature already
-- exists in the catalog but no guild can enable it yet).
CREATE TABLE IF NOT EXISTS dbot_features (
    feature_key         VARCHAR(50)  NOT NULL,
    name                VARCHAR(100) NOT NULL,
    description         VARCHAR(255) NULL,
    is_globally_enabled BOOLEAN      NOT NULL DEFAULT 1,
    PRIMARY KEY (feature_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Generic per-guild feature toggle + config. Replaces the "one config table per
-- feature" pattern (dbot_guild_birthday_config, dbot_guild_event_config, ...).
-- ON DELETE RESTRICT on feature_key: deleting a feature definition must never
-- silently wipe every guild's config for it — that has to be an explicit step.
CREATE TABLE IF NOT EXISTS dbot_guild_features (
    guild_id     BIGINT UNSIGNED NOT NULL,
    feature_key  VARCHAR(50)     NOT NULL,
    enabled      BOOLEAN         NOT NULL DEFAULT 0,
    channel_id   BIGINT UNSIGNED NULL,
    config       JSON            NULL,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, feature_key),
    INDEX idx_feature_enabled (feature_key, enabled),
    CONSTRAINT fk_gf_guild   FOREIGN KEY (guild_id)    REFERENCES dbot_guilds (guild_id)     ON DELETE CASCADE,
    CONSTRAINT fk_gf_feature FOREIGN KEY (feature_key) REFERENCES dbot_features (feature_key) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Guild-wide settings, independent of individual features.
CREATE TABLE IF NOT EXISTS dbot_guild_settings (
    guild_id       BIGINT UNSIGNED NOT NULL,
    locale         VARCHAR(10)     NULL,   -- NULL = fall back to guild.preferred_locale / app default in code
    timezone       VARCHAR(64)     NOT NULL DEFAULT 'UTC',
    mod_role_id    BIGINT UNSIGNED NULL,
    log_channel_id BIGINT UNSIGNED NULL,
    PRIMARY KEY (guild_id),
    CONSTRAINT fk_gs_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Customizable messages/embeds per guild per feature. Missing row → fall back
-- to a hardcoded default template in code.
CREATE TABLE IF NOT EXISTS dbot_guild_feature_messages (
    guild_id     BIGINT UNSIGNED NOT NULL,
    feature_key  VARCHAR(50)     NOT NULL,
    message_key  VARCHAR(50)     NOT NULL,
    content      TEXT            NOT NULL,
    embed_color  INT UNSIGNED    NULL,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, feature_key, message_key),
    CONSTRAINT fk_gfm_guild   FOREIGN KEY (guild_id)    REFERENCES dbot_guilds (guild_id)     ON DELETE CASCADE,
    CONSTRAINT fk_gfm_feature FOREIGN KEY (feature_key) REFERENCES dbot_features (feature_key) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Global user data: properties of the person, independent of guild.
-- Storage strategy: birth_month + birth_day without a year (privacy). region
-- determines when the greeting locally "starts".
CREATE TABLE IF NOT EXISTS dbot_users (
    user_id      BIGINT UNSIGNED                NOT NULL,
    birth_month  TINYINT UNSIGNED               NULL,   -- 1-12, NULL = not set
    birth_day    TINYINT UNSIGNED               NULL,   -- 1-31
    region       ENUM('AMERICAS','EMEA','APAC') NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    INDEX idx_birthday (birth_month, birth_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Birthday feature: opt-in + greeting status per (user, guild). This MAY differ
-- per guild, even though the birthday itself is global.
CREATE TABLE IF NOT EXISTS dbot_user_birthday_status (
    user_id           BIGINT UNSIGNED NOT NULL,
    guild_id          BIGINT UNSIGNED NOT NULL,
    opted_in          BOOLEAN NOT NULL DEFAULT 1,
    last_greeted_year YEAR    NULL DEFAULT NULL,
    PRIMARY KEY (user_id, guild_id),
    INDEX idx_guild (guild_id),
    CONSTRAINT fk_bday_status_user  FOREIGN KEY (user_id)  REFERENCES dbot_users (user_id)   ON DELETE CASCADE,
    CONSTRAINT fk_bday_status_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Events (feature 2)
CREATE TABLE IF NOT EXISTS dbot_events (
    id              BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    guild_id        BIGINT UNSIGNED  NOT NULL,
    created_by      BIGINT UNSIGNED  NOT NULL,
    title           VARCHAR(200)     NOT NULL,
    description     TEXT             NULL,
    event_datetime  DATETIME         NOT NULL,
    timezone        VARCHAR(64)      NOT NULL DEFAULT 'UTC',
    channel_id      BIGINT UNSIGNED  NULL,   -- override; otherwise falls back to dbot_guild_features (feature_key='events')
    reminder_sent   BOOLEAN          NOT NULL DEFAULT 0,
    created_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_guild_event (guild_id, event_datetime),
    CONSTRAINT fk_event_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Reaction roles (feature 3)
CREATE TABLE IF NOT EXISTS dbot_reaction_role_messages (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    guild_id    BIGINT UNSIGNED NOT NULL,
    channel_id  BIGINT UNSIGNED NOT NULL,
    message_id  BIGINT UNSIGNED NOT NULL,
    exclusive   BOOLEAN NOT NULL DEFAULT 0,   -- max 1 role from this set
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_message (message_id),
    CONSTRAINT fk_rrm_guild FOREIGN KEY (guild_id) REFERENCES dbot_guilds (guild_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dbot_reaction_roles (
    reaction_message_id BIGINT UNSIGNED NOT NULL,
    emoji                VARCHAR(64)     NOT NULL,   -- unicode emoji or custom emoji id as string
    role_id              BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (reaction_message_id, emoji),
    CONSTRAINT fk_rr_message FOREIGN KEY (reaction_message_id) REFERENCES dbot_reaction_role_messages (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Seed the feature catalog. reaction_roles isn't built yet → globally disabled
-- (staged rollout: enable once the feature goes live).
INSERT INTO dbot_features (feature_key, name, description, is_globally_enabled) VALUES
    ('birthday',       'Birthdays',      'Greet members on their birthday.', 1),
    ('events',         'Events',         'Server events with reminders.', 1),
    ('reaction_roles',  'Reaction Roles', 'Assign roles via message reactions.', 0)
    AS new
ON DUPLICATE KEY UPDATE name = new.name, description = new.description;