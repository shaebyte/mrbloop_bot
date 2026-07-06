USE mrbloop_db;

-- 1. MEMBERS TABLE
CREATE TABLE IF NOT EXISTS am_members (
    player_id VARCHAR(255) NOT NULL,
    alias VARCHAR(100) NOT NULL,
    ingame_name VARCHAR(100) NOT NULL,
    alliance_name VARCHAR(100) NOT NULL,
    server VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id),
    INDEX idx_members_ingame_name (ingame_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. MEMBER NAME HISTORY TABLE
CREATE TABLE IF NOT EXISTS am_member_name_history (
    id INT AUTO_INCREMENT NOT NULL,
    player_id VARCHAR(255) NOT NULL,
    ingame_name VARCHAR(100) NOT NULL,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME NULL,
    PRIMARY KEY (id),
    INDEX idx_history_ingame_name (ingame_name),
    INDEX idx_history_date_range (valid_from, valid_to),
    FOREIGN KEY (player_id) REFERENCES am_members(player_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. EVENTS TABLE
CREATE TABLE IF NOT EXISTS am_events (
    event_id INT AUTO_INCREMENT NOT NULL,
    event_type ENUM('Tri-Alliance Clash', 'Swordland') NOT NULL,
    legion ENUM('Legion 1', 'Legion 2') NOT NULL,
    event_date DATE NOT NULL,
    total_attendees INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    INDEX idx_event_lookup (event_type, event_date),
    -- Prevents the same event session from being created twice on the same date
    UNIQUE KEY uq_event_session (event_type, legion, event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. EVENT ATTENDANCE (JUNCTION TABLE, DENORMALIZED)
-- event_type and event_date are copied from am_events on insert so that the
-- UNIQUE key below lets MySQL itself enforce the business rule:
-- "a member can participate in only ONE legion per event type per date".
CREATE TABLE IF NOT EXISTS am_event_attendance (
    event_id INT NOT NULL,
    player_id VARCHAR(255) NOT NULL,
    event_type ENUM('Tri-Alliance Clash', 'Swordland') NOT NULL,
    event_date DATE NOT NULL,
    matched_by_name VARCHAR(100) NULL, -- the name the OCR actually read
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, player_id),
    UNIQUE KEY uq_attendance_per_event_day (player_id, event_type, event_date),
    INDEX idx_attendance_event_day (event_type, event_date),
    FOREIGN KEY (event_id) REFERENCES am_events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES am_members(player_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. MEMBER POWER (ONE VALUE PER MEMBER PER DATE, SCREENSHOT-SOURCED)
CREATE TABLE IF NOT EXISTS am_memberpower (
    player_id VARCHAR(255) NOT NULL,
    power_date DATE NOT NULL,
    power BIGINT NOT NULL,
    matched_by_name VARCHAR(100) NULL, -- the name the OCR actually read
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, power_date),
    INDEX idx_memberpower_date (power_date),
    FOREIGN KEY (player_id) REFERENCES am_members(player_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. NAME REFRESH LOG (SINGLE ROW, OVERWRITTEN ON EACH RUN)
-- Tracks when the bulk name-refresh job last completed, so the API can
-- warn when names are stale and enforce a cooldown between runs
-- (the Century Game API rate-limits aggressively).
CREATE TABLE IF NOT EXISTS am_refresh_log (
    id TINYINT NOT NULL,
    finished_at TIMESTAMP NOT NULL,
    total INT NOT NULL,
    changed_count INT NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- If am_event_attendance already exists WITHOUT the denormalized columns,
-- run this migration instead of the CREATE above:
--
-- ALTER TABLE am_event_attendance
--     ADD COLUMN event_type ENUM('Tri-Alliance Clash', 'Swordland') NOT NULL AFTER player_id,
--     ADD COLUMN event_date DATE NOT NULL AFTER event_type;
-- UPDATE am_event_attendance a
--     JOIN am_events e ON e.event_id = a.event_id
--     SET a.event_type = e.event_type, a.event_date = e.event_date;
-- ALTER TABLE am_event_attendance
--     ADD UNIQUE KEY uq_attendance_per_event_day (player_id, event_type, event_date),
--     ADD INDEX idx_attendance_event_day (event_type, event_date);
