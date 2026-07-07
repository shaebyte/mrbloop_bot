"""Attendance statistics."""
from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from app import repository
from app.constants import EVENT_TYPES, LEGIONS

router = APIRouter(prefix="/stats", tags=["stats"])

DEFAULT_STATS_WINDOW_DAYS = 60


@router.get("/attendance")
async def attendance_stats(
    event_type: str | None = None,
    legion: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    alliance_name: str | None = None,
):
    """Per member: attended vs total events in the selected window.

    Members with 0 attendance are included, so you also see who was absent.
    """
    if event_type and event_type not in EVENT_TYPES:
        raise HTTPException(400, f"event_type must be one of: {', '.join(EVENT_TYPES)}")
    if legion and legion not in LEGIONS:
        raise HTTPException(400, f"legion must be one of: {', '.join(LEGIONS)}")

    total_events = await repository.count_events(event_type, legion, date_from, date_to)
    members = await repository.attendance_counts(
        event_type, legion, date_from, date_to, alliance_name
    )
    for m in members:
        m["total_events"] = total_events
        m["percentage"] = round(m["attended"] / total_events * 100, 1) if total_events else 0.0

    return {
        "total_events": total_events,
        "filters": {
            "event_type": event_type,
            "legion": legion,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "alliance_name": alliance_name,
        },
        "members": members,
    }


@router.get("/matrix")
async def attendance_matrix(
    event_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    alliance_name: str | None = None,
):
    """Per member, per (event_type, event_date) session: attended or not, and in which legion.

    Legion is treated as an attribute of a member's participation in a session,
    not as a separate session — matching the rule that a member can only join
    one legion per event type per day.
    """
    if event_type and event_type not in EVENT_TYPES:
        raise HTTPException(400, f"event_type must be one of: {', '.join(EVENT_TYPES)}")

    if not date_from and not date_to:
        date_to = date.today()
        date_from = date_to - timedelta(days=DEFAULT_STATS_WINDOW_DAYS)

    sessions = await repository.event_sessions(event_type, date_from, date_to)
    records = await repository.attendance_matrix(event_type, date_from, date_to, alliance_name)
    members = await repository.list_members(alliance_name, None)

    session_keys = [f"{s['event_type']}|{s['event_date']}" for s in sessions]
    legion_by_member = {}
    for r in records:
        key = f"{r['event_type']}|{r['event_date']}"
        legion_by_member.setdefault(r["player_id"], {})[key] = r["legion"]

    rows = [
        {
            "player_id": m["player_id"],
            "alias": m["alias"],
            "ingame_name": m["ingame_name"],
            "alliance_name": m["alliance_name"],
            "attendance": {
                key: legion_by_member.get(m["player_id"], {}).get(key)
                for key in session_keys
            },
        }
        for m in members
    ]

    return {
        "sessions": [
            {"event_type": s["event_type"], "event_date": str(s["event_date"])} for s in sessions
        ],
        "filters": {
            "event_type": event_type,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "alliance_name": alliance_name,
        },
        "members": rows,
    }


@router.get("/power-matrix")
async def power_matrix(
    date_from: date | None = None,
    date_to: date | None = None,
    alliance_name: str | None = None,
):
    """Per member, per recorded power_date: the power value.

    Defaults to the last 60 days when no dates are given.
    """
    if not date_from and not date_to:
        date_to = date.today()
        date_from = date_to - timedelta(days=DEFAULT_STATS_WINDOW_DAYS)

    dates = await repository.power_dates(date_from, date_to)
    records = await repository.power_matrix(date_from, date_to, alliance_name)
    members = await repository.list_members(alliance_name, None)

    date_keys = [str(d["power_date"]) for d in dates]
    power_by_member: dict[str, dict[str, int]] = {}
    for r in records:
        power_by_member.setdefault(r["player_id"], {})[str(r["power_date"])] = r["power"]

    rows = [
        {
            "player_id": m["player_id"],
            "alias": m["alias"],
            "ingame_name": m["ingame_name"],
            "alliance_name": m["alliance_name"],
            "power": {key: power_by_member.get(m["player_id"], {}).get(key) for key in date_keys},
        }
        for m in members
    ]

    return {
        "dates": date_keys,
        "filters": {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "alliance_name": alliance_name,
        },
        "members": rows,
    }


@router.get("/members/{player_id}")
async def member_stats(player_id: str):
    member = await repository.get_member(player_id)
    if not member:
        raise HTTPException(404, "Member not found")

    events = await repository.member_events(player_id)

    return {
        "player_id": member["player_id"],
        "alias": member["alias"],
        "ingame_name": member["ingame_name"],
        "attended_total": len(events),
        "by_event_type": dict(Counter(e["event_type"] for e in events)),
        "events": events,
    }
