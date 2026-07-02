"""Century Game player API client.

fetch_player_info() does the same "login" call that autoredeemgifts
redeemer.py does before redeeming a gift code: POST {REDEEM_API}/player
with fid + time, signed with md5(form_str + REDEEM_SECRET). That one call
IS the login — there is no separate login step.

The raw response looks like:

    {"code": 0, "data": {"fid": 12345, "nickname": "ShoNuff", "kid": 245, ...}}

fetch_player_info() returns {"player_id", "ingame_name", "server"}, i.e. the
raw "fid"/"nickname"/"kid" renamed to match am_members — callers never see
the game API's field names.
"""
import hashlib
import time

import httpx

from app.config import REDEEM_API, REDEEM_SECRET

_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}


def _sign(form_str: str) -> str:
    return hashlib.md5((form_str + REDEEM_SECRET).encode()).hexdigest()


def is_rate_limited(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


async def fetch_player_info(client: httpx.AsyncClient, player_id: str) -> dict:
    """Returns {"player_id", "ingame_name", "server"} (see module docstring).

    Raises ValueError when the API answers but the player is unknown.
    """
    ts = int(time.time() * 1000)
    form_str = f"fid={player_id}&time={ts}"
    body = f"sign={_sign(form_str)}&{form_str}"
    response = await client.post(f"{REDEEM_API}/player", headers=_HEADERS, data=body, timeout=30.0)
    response.raise_for_status()
    result = response.json()

    if result.get("code") != 0:
        raise ValueError(result.get("msg", "Player not found"))

    data = result.get("data") or {}
    if "nickname" not in data:
        raise ValueError(f"'nickname' missing in API response; got keys: {sorted(data)}")
    return {
        "player_id": str(data["fid"]),
        "ingame_name": str(data["nickname"]),
        "server": str(data.get("kid") or ""),
    }
