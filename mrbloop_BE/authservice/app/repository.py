from app.database import get_pool


async def get_user_by_username(username: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, username, password_hash, role, created_at "
                "FROM auth_users WHERE username = %s",
                (username,),
            )
            return await cur.fetchone()


async def create_user(username: str, password_hash: str, role: str) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO auth_users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
            return cur.lastrowid


async def list_users() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, username, role, created_at FROM auth_users ORDER BY username"
            )
            return await cur.fetchall()


async def get_user_by_id(user_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, username, role, created_at FROM auth_users WHERE id = %s",
                (user_id,),
            )
            return await cur.fetchone()


async def delete_user(user_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM auth_users WHERE id = %s", (user_id,))
            return cur.rowcount > 0


async def update_user_role(user_id: int, role: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE auth_users SET role = %s WHERE id = %s", (role, user_id)
            )
            return cur.rowcount > 0
