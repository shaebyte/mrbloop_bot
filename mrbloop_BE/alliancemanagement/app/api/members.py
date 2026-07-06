"""Member CRUD, name history, and the bulk name-refresh job."""
import httpx
from fastapi import APIRouter, HTTPException

from app import repository
from app.services import name_sync
from app.services.player_api import fetch_player_info

router = APIRouter(prefix="/members", tags=["members"])


# --- Bulk name refresh (fixed paths BEFORE /{player_id}) ---

@router.post("/refresh-names", status_code=202)
async def refresh_names():
    cooldown_left = await name_sync.seconds_until_ready()
    if cooldown_left > 0:
        minutes_left = max(1, round(cooldown_left / 60))
        raise HTTPException(
            429, f"Refresh ran recently, try again in {minutes_left}m"
        )

    started = await name_sync.start_refresh()
    if not started:
        raise HTTPException(409, "A refresh job is already running")
    return {"message": "Refresh started", "total": name_sync.state["total"]}


@router.get("/refresh-names/status")
async def refresh_status():
    last_refresh = await repository.get_last_refresh()
    cooldown_left = await name_sync.seconds_until_ready()
    return {**name_sync.state, "last_refresh": last_refresh, "cooldown_left": cooldown_left}


# --- CRUD ---

@router.get("")
async def list_members(alliance_name: str | None = None, server: str | None = None):
    return await repository.list_members(alliance_name, server)


@router.post("", status_code=201)
async def create_member(body: dict):
    player_id = str(body.get("player_id") or "").strip()
    alias = str(body.get("alias") or "").strip()
    alliance_name = str(body.get("alliance_name") or "").strip()
    if not player_id or not alias or not alliance_name:
        raise HTTPException(400, "player_id, alias and alliance_name are required")

    if await repository.member_exists(player_id):
        raise HTTPException(409, "player_id already exists")

    try:
        async with httpx.AsyncClient() as client:
            info = await fetch_player_info(client, player_id)
    except ValueError as e:
        raise HTTPException(404, f"Player API: {e}")
    except httpx.HTTPError:
        raise HTTPException(502, "Game API unreachable, try again later.")

    await repository.create_member(
        player_id, alias, info["ingame_name"], alliance_name, info["server"]
    )
    return await repository.get_member(player_id)


@router.get("/{player_id}")
async def get_member(player_id: str):
    member = await repository.get_member(player_id)
    if not member:
        raise HTTPException(404, "Member not found")
    return member


@router.patch("/{player_id}")
async def update_member(player_id: str, body: dict):
    # Only these columns may be changed; ingame_name/server come from the game API.
    fields = {}
    for key in ("alias", "alliance_name"):
        value = str(body.get(key) or "").strip()
        if value:
            fields[key] = value
    if not fields:
        raise HTTPException(400, "Nothing to update")

    if not await repository.member_exists(player_id):
        raise HTTPException(404, "Member not found")

    await repository.update_member(player_id, fields)
    return await repository.get_member(player_id)


@router.delete("/{player_id}", status_code=204)
async def delete_member(player_id: str):
    if not await repository.member_exists(player_id):
        raise HTTPException(404, "Member not found")
    await repository.delete_member(player_id)


@router.get("/{player_id}/name-history")
async def name_history(player_id: str):
    if not await repository.member_exists(player_id):
        raise HTTPException(404, "Member not found")
    return await repository.get_name_history(player_id)
