import asyncio
import logging

from app.database import create_pool, close_pool
from app.poller import run_poller

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


async def main() -> None:
    await create_pool()
    try:
        await run_poller()
    finally:
        await close_pool()


if __name__ == '__main__':
    asyncio.run(main())
