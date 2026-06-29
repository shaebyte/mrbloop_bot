from fastapi import APIRouter, Depends, Query
from ..deps import get_db
from ..auth import require_mod

router = APIRouter(
    prefix="/redeem-attempts",
    tags=["redeem"],
    dependencies=[Depends(require_mod)],
)


@router.get("")
async def list_attempts(
    db=Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    status: str = Query("all"),
):
    offset = (page - 1) * limit

    conditions = []
    params = []

    if search:
        conditions.append("(player_id LIKE %s OR gift_code LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]

    if status in ("success", "failed"):
        conditions.append("status = %s")
        params.append(status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_result = await db.execute(
        f"SELECT COUNT(*) AS total FROM arg_redeem_attempts {where}", params
    )
    total = (await count_result.fetchone())["total"]

    items_result = await db.execute(
        f"""
        SELECT player_id, gift_code, status, attempt_count, error_message,
               DATE(redeemed_at) AS redeemed_at
        FROM arg_redeem_attempts
        {where}
        ORDER BY redeemed_at DESC
        LIMIT %s OFFSET %s
        """,
        params + [limit, offset],
    )
    items = await items_result.fetchall()

    return {"items": items, "total": total}
