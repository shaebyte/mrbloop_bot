"""Attendance statistics."""
from collections import Counter
from datetime import date

from fastapi import APIRouter, HTTPException

from app import repository
from app.constants import EVENT_TYPES, LEGIONS

router = APIRouter(prefix="/stats", tags=["stats"])


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
