"""Bulk in-game name refresh + name history bookkeeping.

Runs as a background task. Processes members sequentially with a delay
between accounts (the Century Game API rate-limits aggressively), with
retry/backoff semantics mirroring redeemer.py.
"""
import asyncio
import logging
from datetime import datetime

import httpx

from app import repository
from app.services.player_api import fetch_player_info, is_rate_limited

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_BACKOFF = 5
RATE_LIMIT_BACKOFF = 60
INTER_ACCOUNT_DELAY = 3
COOLDOWN = 3600  # minimum seconds between refresh runs

# Progress of the running/last refresh job.
# Served as-is by GET /members/refresh-names/status.
state = {
    "running": False,
    "total": 0,
    "processed": 0,
    "changed": [],   # [{player_id, alias, old_name, new_name}]
    "errors": [],    # [{player_id, alias, error}]
    "started_at": None,
    "finished_at": None,
}

async def _refresh_one(client: httpx.AsyncClient, player_id: str) -> None:
    member = await repository.get_member(player_id)
    if member is None:  # deleted while the job was running
        return

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            info = await fetch_player_info(client, player_id)
            new_name = info["ingame_name"]
            new_server = info["server"]

            if new_name != member["ingame_name"]:
                await repository.save_name_change(player_id, new_name)
                state["changed"].append({
                    "player_id": player_id,
                    "alias": member["alias"],
                    "old_name": member["ingame_name"],
                    "new_name": new_name,
                })
                logger.info(
                    "Name change %s (%s): %r -> %r",
                    member["alias"], player_id, member["ingame_name"], new_name,
                )
            if new_server and new_server != member["server"]:
                await repository.update_server(player_id, new_server)
            return

        except ValueError as exc:
            # Permanent (player not found etc.) — retrying won't help.
            state["errors"].append(
                {"player_id": player_id, "alias": member["alias"], "error": str(exc)}
            )
            logger.error("Refresh %s (%s) failed: %s", member["alias"], player_id, exc)
            return

        except Exception as exc:  # network errors, 429, 5xx, ...
            if attempt < MAX_ATTEMPTS:
                backoff = RATE_LIMIT_BACKOFF if is_rate_limited(exc) else RETRY_BACKOFF
                logger.warning(
                    "Refresh %s (%s) attempt %d error (%s), retrying in %ds...",
                    member["alias"], player_id, attempt, exc, backoff,
                )
                await asyncio.sleep(backoff)
            else:
                state["errors"].append(
                    {"player_id": player_id, "alias": member["alias"], "error": str(exc)}
                )
                logger.error(
                    "Refresh %s (%s) failed after %d attempts: %s",
                    member["alias"], player_id, attempt, exc,
                )


async def _run_refresh(player_ids: list[str]) -> None:
    try:
        async with httpx.AsyncClient() as client:
            for player_id in player_ids:
                await _refresh_one(client, player_id)
                state["processed"] += 1
                await asyncio.sleep(INTER_ACCOUNT_DELAY)
    finally:
        state["running"] = False
        state["finished_at"] = datetime.now()
        await repository.save_refresh_log(
            state["finished_at"], state["total"], len(state["changed"])
        )
        logger.info(
            "Name refresh finished: %d processed, %d changed, %d errors",
            state["processed"], len(state["changed"]), len(state["errors"]),
        )


async def seconds_until_ready() -> float:
    """0 if a refresh may start now, otherwise seconds left on the cooldown."""
    last = await repository.get_last_refresh()
    if last is None:
        return 0
    elapsed = (datetime.now() - last["finished_at"]).total_seconds()
    return max(0, COOLDOWN - elapsed)


async def start_refresh() -> bool:
    """Kick off a background refresh of all members. Returns False if already running."""
    if state["running"]:
        return False
    state.update(
        running=True, total=0, processed=0, changed=[], errors=[],
        started_at=datetime.now(), finished_at=None,
    )
    player_ids = await repository.get_all_player_ids()
    state["total"] = len(player_ids)

    asyncio.create_task(_run_refresh(player_ids))
    return True
