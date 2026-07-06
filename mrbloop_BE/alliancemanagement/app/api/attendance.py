"""Screenshot attendance flow.

Two steps so an OCR mistake never silently writes wrong attendance:

1. POST /attendance/preview  — multipart upload of screenshots + event info.
   Screenshots are processed fully in-memory and never stored. Returns the
   matched members for the leader to review in the frontend.
2. POST /attendance/confirm  — the (possibly corrected) list of player_ids.
   Upserts the event and writes attendance. The denormalized UNIQUE key
   (player_id, event_type, event_date) guarantees one legion per event per
   day; conflicts are detected up-front and reported instead of raising.
"""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import repository
from app.constants import EVENT_TYPES, LEGIONS
from app.services import matching, ocr

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _check_event_fields(event_type: str, legion: str) -> None:
    if event_type not in EVENT_TYPES:
        raise HTTPException(400, f"event_type must be one of: {', '.join(EVENT_TYPES)}")
    if legion not in LEGIONS:
        raise HTTPException(400, f"legion must be one of: {', '.join(LEGIONS)}")


@router.post("/preview")
async def preview_attendance(
    event_type: str = Form(...),
    legion: str = Form(...),
    event_date: date = Form(...),
    total_attendees: int = Form(...),
    screenshots: list[UploadFile] = File(...),
):
    _check_event_fields(event_type, legion)
    if total_attendees <= 0:
        raise HTTPException(400, "total_attendees must be a positive number")
    if not screenshots:
        raise HTTPException(400, "At least one screenshot required")

    all_lines: list[dict] = []
    for upload in screenshots:
        if upload.content_type and not upload.content_type.startswith("image/"):
            raise HTTPException(
                415, f"'{upload.filename}' is not an image ({upload.content_type})"
            )
        data = await upload.read()  # in-memory only, never written to disk
        all_lines.extend(await ocr.extract_lines(data))

    members = await repository.get_members_for_matching()

    # History names that were valid at any moment on the event date.
    day_start = datetime.combine(event_date, time.min)
    day_end = day_start + timedelta(days=1)
    history_rows = await repository.get_history_names_between(day_start, day_end)

    candidates = matching.filter_candidates(all_lines)
    result = matching.match_lines(members, history_rows, candidates)

    return {
        "event_type": event_type,
        "legion": legion,
        "event_date": event_date,
        "total_attendees": total_attendees,
        "screenshots_processed": len(screenshots),
        "lines_read": len(all_lines),
        "candidates_considered": len(candidates),
        "matched": result["matched"],
        "unmatched_lines": result["unmatched_lines"],
        "members_not_found": result["members_not_found"],
    }


@router.post("/confirm")
async def confirm_attendance(body: dict):
    event_type = str(body.get("event_type") or "")
    legion = str(body.get("legion") or "")
    _check_event_fields(event_type, legion)

    try:
        event_date = date.fromisoformat(str(body.get("event_date") or ""))
    except ValueError:
        raise HTTPException(400, "event_date must be a date like 2026-07-02")

    total_attendees = body.get("total_attendees")
    if not isinstance(total_attendees, int) or isinstance(total_attendees, bool) or total_attendees <= 0:
        raise HTTPException(400, "total_attendees must be a positive number")

    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        raise HTTPException(400, "entries must be a non-empty list")

    # player_id -> matched_by_name (the OCR text, or None for manual entries)
    requested: dict[str, str | None] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise HTTPException(400, "every entry must be an object with a player_id")
        player_id = str(entry.get("player_id") or "").strip()
        if not player_id:
            raise HTTPException(400, "every entry must have a player_id")
        requested[player_id] = entry.get("matched_by_name")

    # Get or create the event session (event_type, legion, event_date is UNIQUE).
    event = await repository.find_event(event_type, legion, event_date)
    if event:
        event_id = event["event_id"]
        await repository.update_event_total_attendees(event_id, total_attendees)
    else:
        event_id = await repository.create_event(event_type, legion, event_date, total_attendees)

    # Which player_ids actually exist as members?
    rows = await repository.find_members(list(requested))
    known = {row["player_id"]: row["alias"] for row in rows}
    unknown = sorted(set(requested) - set(known))

    # Existing attendance for this event type + date (any legion) for these players.
    registrations = await repository.get_registrations(list(known), event_type, event_date)
    existing = {row["player_id"]: row for row in registrations}

    added: list[str] = []
    already: list[str] = []
    conflicts: list[dict] = []

    for player_id in sorted(known):
        row = existing.get(player_id)
        if row is not None:
            if row["event_id"] == event_id:
                already.append(player_id)
            else:
                conflicts.append({
                    "player_id": player_id,
                    "alias": known[player_id],
                    "registered_in_legion": row["legion"],
                })
            continue

        await repository.add_attendance(
            event_id, player_id, event_type, event_date, requested[player_id]
        )
        added.append(player_id)

    return {
        "event_id": event_id,
        "added": added,
        "already_registered": already,
        "conflicts": conflicts,
        "unknown_player_ids": unknown,
    }
