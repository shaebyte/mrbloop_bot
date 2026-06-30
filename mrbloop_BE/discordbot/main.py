"""
mrbloop_BE – entrypoint

Usage:
    cd mrbloop_BE
    python main.py
"""

import asyncio
import logging
import sys

from config import settings
from core import MrBloopBot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("discord").setLevel(logging.WARNING)


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    if not settings.DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is not set in .env!")
        sys.exit(1)

    bot = MrBloopBot()
    try:
        await bot.start(settings.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Stopped via KeyboardInterrupt")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
