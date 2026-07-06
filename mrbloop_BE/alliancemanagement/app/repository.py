"""All SQL queries, in the same style as the discordbot repositories.

Every function acquires a connection from the pool, runs its query and
returns plain dicts (the pool uses DictCursor + autocommit).
"""
import logging
from datetime import datetime, timezone

from app.database import get_pool

logger = logging.getLogger(__name__)

MEMBER_COLS = "player_id, alias, ingame_name, alliance_name, server, updated_at"


def _event_filters(event_type, legion, date_from, date_to) -> tuple[str, list]:
    """Build a WHERE clause for filters on the am_events table (alias e)."""
    conditions = []
    params: list = []
    if event_type:
        conditions.append("e.event_type = %s")
        params.append(event_type)
    if legion:
        conditions.append("e.legion = %s")
        params.append(legion)
    if date_from:
        conditions.append("e.event_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("e.event_date <= %s")
        params.append(date_to)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


# ─── Members ─────────────────────────────────────────────────────────────────

async def list_members(alliance_name: str | None, server: str | None) -> list[dict]:
    conditions = []
    params: list = []
    if alliance_name:
        conditions.append("alliance_name = %s")
        params.append(alliance_name)
    if server:
        conditions.append("server = %s")
        params.append(server)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {MEMBER_COLS} FROM am_members {where} ORDER BY alias", params
            )
            return await cur.fetchall()


async def get_member(player_id: str) -> dict | None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {MEMBER_COLS} FROM am_members WHERE player_id = %s",
                (player_id,),
            )
            return await cur.fetchone()


async def member_exists(player_id: str) -> bool:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM am_members WHERE player_id = %s", (player_id,)
            )
            return await cur.fetchone() is not None


async def create_member(
    player_id: str, alias: str, ingame_name: str, alliance_name: str, server: str
) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO am_members (player_id, alias, ingame_name, alliance_name, server)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (player_id, alias, ingame_name, alliance_name, server),
            )
            # First row in the name history
            await cur.execute(
                "INSERT INTO am_member_name_history (player_id, ingame_name, valid_from) VALUES (%s, %s, %s)",
                (player_id, ingame_name, datetime.now()),
            )


async def update_member(player_id: str, fields: dict) -> None:
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE am_members SET {set_clause} WHERE player_id = %s",
                (*fields.values(), player_id),
            )


async def delete_member(player_id: str) -> None:
    # history + attendance cascade in the DB
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM am_members WHERE player_id = %s", (player_id,))


async def get_name_history(player_id: str) -> list[dict]:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, ingame_name, valid_from, valid_to
                FROM am_member_name_history
                WHERE player_id = %s
                ORDER BY valid_from DESC
                """,
                (player_id,),
            )
            return await cur.fetchall()


async def get_all_player_ids() -> list[str]:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT player_id FROM am_members ORDER BY alias")
            rows = await cur.fetchall()
            return [row["player_id"] for row in rows]


async def save_name_change(player_id: str, new_name: str) -> None:
    """Close the open history row, insert the new name and update the member."""
    now = datetime.now()
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE am_member_name_history SET valid_to = %s WHERE player_id = %s AND valid_to IS NULL",
                (now, player_id),
            )
            await cur.execute(
                "INSERT INTO am_member_name_history (player_id, ingame_name, valid_from) VALUES (%s, %s, %s)",
                (player_id, new_name, now),
            )
            await cur.execute(
                "UPDATE am_members SET ingame_name = %s WHERE player_id = %s",
                (new_name, player_id),
            )


async def update_server(player_id: str, server: str) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE am_members SET server = %s WHERE player_id = %s",
                (server, player_id),
            )


async def get_last_refresh() -> dict | None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT finished_at, total, changed_count FROM am_refresh_log WHERE id = 1"
            )
            row = await cur.fetchone()
            # MySQL DATETIME columns strip tzinfo; the value stored is always
            # UTC wall-clock (see name_sync.py), so re-tag it before it's
            # compared against an aware "now" or serialized to the frontend.
            if row and row["finished_at"] is not None:
                row["finished_at"] = row["finished_at"].replace(tzinfo=timezone.utc)
            return row


async def save_refresh_log(finished_at: datetime, total: int, changed_count: int) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO am_refresh_log (id, finished_at, total, changed_count)
                VALUES (1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    finished_at = VALUES(finished_at),
                    total = VALUES(total),
                    changed_count = VALUES(changed_count)
                """,
                (finished_at, total, changed_count),
            )


async def get_members_for_matching() -> list[dict]:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT player_id, alias, ingame_name FROM am_members")
            return await cur.fetchall()


async def get_history_names_between(day_start: datetime, day_end: datetime) -> list[dict]:
    """History names that were valid at any moment in the given window."""
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT player_id, ingame_name FROM am_member_name_history
                WHERE valid_from < %s AND (valid_to IS NULL OR valid_to >= %s)
                """,
                (day_end, day_start),
            )
            return await cur.fetchall()


async def find_members(player_ids: list[str]) -> list[dict]:
    """Which of these player_ids exist? Returns player_id + alias per hit."""
    if not player_ids:
        return []
    placeholders = ", ".join(["%s"] * len(player_ids))
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT player_id, alias FROM am_members WHERE player_id IN ({placeholders})",
                player_ids,
            )
            return await cur.fetchall()


# ─── Events ──────────────────────────────────────────────────────────────────

async def list_events(event_type, legion, date_from, date_to) -> list[dict]:
    where, params = _event_filters(event_type, legion, date_from, date_to)
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT e.event_id, e.event_type, e.legion, e.event_date, e.total_attendees, e.created_at,
                       COUNT(a.player_id) AS attendee_count
                FROM am_events e
                LEFT JOIN am_event_attendance a ON a.event_id = e.event_id
                {where}
                GROUP BY e.event_id
                ORDER BY e.event_date DESC, e.event_type, e.legion
                """,
                params,
            )
            return await cur.fetchall()


async def get_event(event_id: int) -> dict | None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT event_id, event_type, legion, event_date, total_attendees, created_at FROM am_events WHERE event_id = %s",
                (event_id,),
            )
            return await cur.fetchone()


async def find_event(event_type: str, legion: str, event_date) -> dict | None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT event_id FROM am_events WHERE event_type = %s AND legion = %s AND event_date = %s",
                (event_type, legion, event_date),
            )
            return await cur.fetchone()


async def create_event(event_type: str, legion: str, event_date, total_attendees: int) -> int:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO am_events (event_type, legion, event_date, total_attendees) VALUES (%s, %s, %s, %s)",
                (event_type, legion, event_date, total_attendees),
            )
            return cur.lastrowid


async def update_event_total_attendees(event_id: int, total_attendees: int) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE am_events SET total_attendees = %s WHERE event_id = %s",
                (total_attendees, event_id),
            )


async def delete_event(event_id: int) -> None:
    # attendance cascades in the DB
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM am_events WHERE event_id = %s", (event_id,))


async def get_attendees(event_id: int) -> list[dict]:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT m.player_id, m.alias, m.ingame_name, m.alliance_name,
                       a.matched_by_name, a.registered_at
                FROM am_event_attendance a
                JOIN am_members m ON m.player_id = a.player_id
                WHERE a.event_id = %s
                ORDER BY m.alias
                """,
                (event_id,),
            )
            return await cur.fetchall()


# ─── Attendance ──────────────────────────────────────────────────────────────

async def find_registration(player_id: str, event_type: str, event_date) -> dict | None:
    """Is this member already registered for this event type on this date (any legion)?"""
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT event_id FROM am_event_attendance
                WHERE player_id = %s AND event_type = %s AND event_date = %s
                """,
                (player_id, event_type, event_date),
            )
            return await cur.fetchone()


async def get_registrations(player_ids: list[str], event_type: str, event_date) -> list[dict]:
    """Existing registrations (with legion) for these players on this event type + date."""
    if not player_ids:
        return []
    placeholders = ", ".join(["%s"] * len(player_ids))
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT a.player_id, a.event_id, e.legion
                FROM am_event_attendance a
                JOIN am_events e ON e.event_id = a.event_id
                WHERE a.event_type = %s AND a.event_date = %s
                  AND a.player_id IN ({placeholders})
                """,
                [event_type, event_date, *player_ids],
            )
            return await cur.fetchall()


async def add_attendance(
    event_id: int, player_id: str, event_type: str, event_date, matched_by_name: str | None
) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO am_event_attendance
                    (event_id, player_id, event_type, event_date, matched_by_name)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (event_id, player_id, event_type, event_date, matched_by_name),
            )


async def attendance_exists(event_id: int, player_id: str) -> bool:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM am_event_attendance WHERE event_id = %s AND player_id = %s",
                (event_id, player_id),
            )
            return await cur.fetchone() is not None


async def remove_attendance(event_id: int, player_id: str) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM am_event_attendance WHERE event_id = %s AND player_id = %s",
                (event_id, player_id),
            )


# ─── Member power ────────────────────────────────────────────────────────────

async def get_power_for_date(player_ids: list[str], power_date) -> list[dict]:
    """Existing am_memberpower rows for these players on this date."""
    if not player_ids:
        return []
    placeholders = ", ".join(["%s"] * len(player_ids))
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT player_id, power FROM am_memberpower
                WHERE power_date = %s AND player_id IN ({placeholders})
                """,
                [power_date, *player_ids],
            )
            return await cur.fetchall()


async def upsert_member_power(
    player_id: str, power_date, power: int, matched_by_name: str | None
) -> None:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO am_memberpower (player_id, power_date, power, matched_by_name)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    power = VALUES(power),
                    matched_by_name = VALUES(matched_by_name)
                """,
                (player_id, power_date, power, matched_by_name),
            )


def _power_filters(date_from, date_to) -> tuple[str, list]:
    conditions = []
    params: list = []
    if date_from:
        conditions.append("power_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("power_date <= %s")
        params.append(date_to)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


async def power_dates(date_from, date_to) -> list[dict]:
    """Distinct power_date values recorded in the window, oldest first."""
    where, params = _power_filters(date_from, date_to)
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT DISTINCT power_date FROM am_memberpower {where} ORDER BY power_date",
                params,
            )
            return await cur.fetchall()


async def power_matrix(date_from, date_to, alliance_name) -> list[dict]:
    """One row per (member, power_date) recorded in the window."""
    conditions = []
    params: list = []
    if date_from:
        conditions.append("p.power_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("p.power_date <= %s")
        params.append(date_to)
    if alliance_name:
        conditions.append("m.alliance_name = %s")
        params.append(alliance_name)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT p.player_id, p.power_date, p.power
                FROM am_memberpower p
                JOIN am_members m ON m.player_id = p.player_id
                {where}
                """,
                params,
            )
            return await cur.fetchall()


# ─── Statistics ──────────────────────────────────────────────────────────────

async def count_events(event_type, legion, date_from, date_to) -> int:
    """Distinct (event_type, event_date) sessions — Legion 1/2 are the same session."""
    where, params = _event_filters(event_type, legion, date_from, date_to)
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(DISTINCT event_type, event_date) AS total FROM am_events e {where}",
                params,
            )
            row = await cur.fetchone()
            return row["total"]


async def event_sessions(event_type, date_from, date_to) -> list[dict]:
    """Distinct (event_type, event_date) sessions in the window, most recent first."""
    where, params = _event_filters(event_type, None, date_from, date_to)
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT DISTINCT e.event_type, e.event_date
                FROM am_events e
                {where}
                ORDER BY e.event_date DESC, e.event_type
                """,
                params,
            )
            return await cur.fetchall()


async def attendance_matrix(event_type, date_from, date_to, alliance_name) -> list[dict]:
    """One row per (member, session) attended: which legion they joined that day."""
    conditions = []
    params: list = []
    if event_type:
        conditions.append("e.event_type = %s")
        params.append(event_type)
    if date_from:
        conditions.append("e.event_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("e.event_date <= %s")
        params.append(date_to)
    if alliance_name:
        conditions.append("m.alliance_name = %s")
        params.append(alliance_name)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT a.player_id, a.event_type, a.event_date, e.legion
                FROM am_event_attendance a
                JOIN am_events e ON e.event_id = a.event_id
                JOIN am_members m ON m.player_id = a.player_id
                {where}
                """,
                params,
            )
            return await cur.fetchall()


async def attendance_counts(event_type, legion, date_from, date_to, alliance_name) -> list[dict]:
    """Per member: how many of the filtered events they attended (0 included)."""
    where, params = _event_filters(event_type, legion, date_from, date_to)
    member_where = "WHERE m.alliance_name = %s" if alliance_name else ""
    member_params = [alliance_name] if alliance_name else []

    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT m.player_id, m.alias, m.ingame_name, m.alliance_name,
                       COUNT(att.event_id) AS attended
                FROM am_members m
                LEFT JOIN (
                    SELECT a.player_id, a.event_id
                    FROM am_event_attendance a
                    JOIN am_events e ON e.event_id = a.event_id
                    {where}
                ) att ON att.player_id = m.player_id
                {member_where}
                GROUP BY m.player_id
                ORDER BY attended DESC, m.alias
                """,
                [*params, *member_params],
            )
            return await cur.fetchall()


async def member_events(player_id: str) -> list[dict]:
    async with get_pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT e.event_id, e.event_type, e.legion, e.event_date, a.matched_by_name
                FROM am_event_attendance a
                JOIN am_events e ON e.event_id = a.event_id
                WHERE a.player_id = %s
                ORDER BY e.event_date DESC
                """,
                (player_id,),
            )
            return await cur.fetchall()
