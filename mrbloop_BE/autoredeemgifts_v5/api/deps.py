import aiomysql
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

_pool: aiomysql.Pool | None = None


async def _get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            minsize=1,
            maxsize=10,
            autocommit=False,
        )
    return _pool


class _CursorResult:
    """Wraps a DictCursor so routes can use it as an async context manager."""
    def __init__(self, cur: aiomysql.DictCursor):
        self._cur = cur

    async def fetchone(self):
        return await self._cur.fetchone()

    async def fetchall(self):
        return await self._cur.fetchall()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


class _DB:
    def __init__(self, conn: aiomysql.Connection, cur: aiomysql.DictCursor):
        self._conn = conn
        self._cur = cur

    async def execute(self, sql: str, params=()) -> _CursorResult:
        await self._cur.execute(sql, params)
        return _CursorResult(self._cur)

    async def commit(self) -> None:
        await self._conn.commit()


async def get_db():
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            yield _DB(conn, cur)
