"""Screenshot member-power flow, mirroring attendance.py's preview/confirm shape.

1. POST /power/preview  — multipart upload of leaderboard screenshots + date.
   Screenshots are processed fully in-memory and never stored. Returns each
   matched member with the OCR'd power value for the leader to review/correct.
2. POST /power/confirm  — the (possibly corrected) list of {player_id, power}.
   Upserts one am_memberpower row per member per date (re-confirming the same
   date overwrites the previous value for that member).
"""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import repository
from app.services import ocr, power_matching

router = APIRouter(prefix="/power", tags=["power"])


@router.post("/preview")
async def preview_power(
    power_date: date = Form(...),
    screenshots: list[UploadFile] = File(...),
):
    if not screenshots:
        raise HTTPException(400, "At least one screenshot required")

    lines_per_screenshot: list[list[dict]] = []
    for upload in screenshots:
        if upload.content_type and not upload.content_type.startswith("image/"):
            raise HTTPException(
                415, f"'{upload.filename}' is not an image ({upload.content_type})"
            )
        data = await upload.read()  # in-memory only, never written to disk
        lines_per_screenshot.append(await ocr.extract_lines(data))

    members = await repository.get_members_for_matching()

    day_start = datetime.combine(power_date, time.min)
    day_end = day_start + timedelta(days=1)
    history_rows = await repository.get_history_names_between(day_start, day_end)

    result = power_matching.match_power_rows(members, history_rows, lines_per_screenshot)

    lines_read = sum(len(lines) for lines in lines_per_screenshot)
    return {
        "power_date": power_date,
        "screenshots_processed": len(screenshots),
        "lines_read": lines_read,
        "matched": result["matched"],
        "unmatched_rows": result["unmatched_rows"],
        "members_not_found": result["members_not_found"],
    }


@router.post("/confirm")
async def confirm_power(body: dict):
    try:
        power_date = date.fromisoformat(str(body.get("power_date") or ""))
    except ValueError:
        raise HTTPException(400, "power_date must be a date like 2026-07-02")

    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        raise HTTPException(400, "entries must be a non-empty list")

    # player_id -> (power, matched_by_name)
    requested: dict[str, tuple[int, str | None]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise HTTPException(400, "every entry must be an object with a player_id and power")
        player_id = str(entry.get("player_id") or "").strip()
        if not player_id:
            raise HTTPException(400, "every entry must have a player_id")
        power = entry.get("power")
        if not isinstance(power, int) or isinstance(power, bool) or power <= 0:
            raise HTTPException(400, f"power for {player_id} must be a positive number")
        requested[player_id] = (power, entry.get("matched_by_name"))

    rows = await repository.find_members(list(requested))
    known = {row["player_id"]: row["alias"] for row in rows}
    unknown = sorted(set(requested) - set(known))

    existing_rows = await repository.get_power_for_date(list(known), power_date)
    existing = {row["player_id"] for row in existing_rows}

    added: list[str] = []
    updated: list[str] = []
    for player_id in sorted(known):
        power, matched_by_name = requested[player_id]
        await repository.upsert_member_power(player_id, power_date, power, matched_by_name)
        (updated if player_id in existing else added).append(player_id)

    return {
        "power_date": power_date,
        "added": added,
        "updated": updated,
        "unknown_player_ids": unknown,
    }
