import aiomysql
from app.database import get_pool


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
    async with get_pool().acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            yield _DB(conn, cur)
