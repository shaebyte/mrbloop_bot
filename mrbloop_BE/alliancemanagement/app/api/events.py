"""Event listing, detail (with attendees) and manual attendance corrections."""
from datetime import date

from fastapi import APIRouter, HTTPException

from app import repository
from app.constants import EVENT_TYPES, LEGIONS

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    event_type: str | None = None,
    legion: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    if event_type and event_type not in EVENT_TYPES:
        raise HTTPException(400, f"event_type must be one of: {', '.join(EVENT_TYPES)}")
    if legion and legion not in LEGIONS:
        raise HTTPException(400, f"legion must be one of: {', '.join(LEGIONS)}")
    return await repository.list_events(event_type, legion, date_from, date_to)


@router.get("/{event_id}")
async def get_event(event_id: int):
    event = await repository.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    event["attendees"] = await repository.get_attendees(event_id)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int):
    if not await repository.get_event(event_id):
        raise HTTPException(404, "Event not found")
    await repository.delete_event(event_id)


@router.post("/{event_id}/attendance", status_code=201)
async def add_attendee(event_id: int, body: dict):
    """Manual correction: mark a member present without a screenshot."""
    player_id = str(body.get("player_id") or "").strip()
    if not player_id:
        raise HTTPException(400, "player_id is required")

    event = await repository.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    if not await repository.member_exists(player_id):
        raise HTTPException(404, "Member not found")

    existing = await repository.find_registration(
        player_id, event["event_type"], event["event_date"]
    )
    if existing:
        if existing["event_id"] == event_id:
            raise HTTPException(409, "Already registered for this event")
        raise HTTPException(
            409, "Already registered in the other legion for this event type and date"
        )

    # matched_by_name=None: manual entry, no OCR name
    await repository.add_attendance(
        event_id, player_id, event["event_type"], event["event_date"], None
    )
    return {"message": "Attendance added"}


@router.delete("/{event_id}/attendance/{player_id}", status_code=204)
async def remove_attendee(event_id: int, player_id: str):
    if not await repository.attendance_exists(event_id, player_id):
        raise HTTPException(404, "Attendance record not found")
    await repository.remove_attendance(event_id, player_id)
