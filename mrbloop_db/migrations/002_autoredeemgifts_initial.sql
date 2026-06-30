-- ============================================================
-- Migration 002: autoredeemgifts schema – initial tables
-- Run as root:
--   mysql -u root -p < migrations/002_autoredeemgifts_initial.sql
-- ============================================================

USE mrbloop_db;

CREATE TABLE IF NOT EXISTS arg_gift_codes (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    code       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS arg_accounts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    player_id   VARCHAR(255) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    blacklisted TINYINT(1) NOT NULL DEFAULT 0,
    comments    TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS arg_redeem_attempts (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    gift_code     VARCHAR(255) NOT NULL,
    player_id     VARCHAR(255) NOT NULL,
    status        VARCHAR(50)  NOT NULL,
    attempt_count INT NOT NULL DEFAULT 1,
    error_message TEXT,
    redeemed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_code_player (gift_code, player_id),
    FOREIGN KEY (gift_code) REFERENCES arg_gift_codes(code),
    FOREIGN KEY (player_id) REFERENCES arg_accounts(player_id)
);
