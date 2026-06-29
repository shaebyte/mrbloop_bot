import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from ..deps import get_db
from ..auth import require_mod
from ..limiter import limiter
from app.redeemer import fetch_player_info
from app.config import REDEEM_API

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    player_id: str
    name: str


class AccountUpdate(BaseModel):
    name: str | None = None
    blacklisted: bool | None = None
    comments: str | None = None

# --- Public ---

@router.post("", status_code=201)
@limiter.limit("5/minute")
async def create_account(request: Request, body: AccountCreate, db=Depends(get_db)):
    try:
        await db.execute(
            "INSERT INTO arg_accounts (player_id, name) VALUES (%s, %s)",
            (body.player_id, body.name),
        )
        await db.commit()
    except Exception:
        raise HTTPException(409, "Account already exists")
    return {"player_id": body.player_id}

@router.get("/validate/{player_id}")
async def validate_player(player_id: str):
    try:
        data = await fetch_player_info(player_id, REDEEM_API)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=404, detail="Player not found in game.")
    except Exception:
        raise HTTPException(status_code=502, detail="Game API unreachable, try again later.")

@router.get("/{player_id}")
async def get_account(player_id: str, db=Depends(get_db)):
    result = await db.execute(
        "SELECT player_id, name, blacklisted, created_at FROM arg_accounts WHERE player_id = %s",
        (player_id,),
    )
    row = await result.fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row

# --- Moderator ---

@router.get("", dependencies=[Depends(require_mod)])
async def list_accounts(
    db=Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    search: str = Query("", max_length=100),
    status: str = Query("all", pattern="^(all|active|banned)$"),
):
    offset = (page - 1) * limit

    conditions = []
    params: list = []

    if search:
        pattern = f"%{search}%"
        conditions.append("(player_id LIKE %s OR name LIKE %s)")
        params.extend([pattern, pattern])

    if status == "active":
        conditions.append("blacklisted = 0")
    elif status == "banned":
        conditions.append("blacklisted = 1")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_result = await db.execute(
        f"SELECT COUNT(*) AS total FROM arg_accounts {where}", params
    )
    total = (await count_result.fetchone())["total"]

    items_result = await db.execute(
        f"""SELECT player_id, name, blacklisted, comments, created_at
            FROM arg_accounts {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s""",
        [*params, limit, offset],
    )
    items = await items_result.fetchall()

    return {"items": items, "total": total}


@router.put("/{player_id}", dependencies=[Depends(require_mod)])
async def update_account(player_id: str, body: AccountUpdate, db=Depends(get_db)):
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "Nothing to update")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    await db.execute(
        f"UPDATE arg_accounts SET {set_clause} WHERE player_id = %s",
        (*fields.values(), player_id),
    )
    await db.commit()
    return {"ok": True}
