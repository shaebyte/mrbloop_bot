import os
from pathlib import Path
from dotenv import load_dotenv

def _find_repo_root(start: Path, marker: str = "db.env") -> Path | None:
    for directory in (start, *start.parents):
        if (directory / marker).exists():
            return directory
    return None

# Shared DB credentials from the root db.env (only relevant outside Docker;
# in Docker, docker-compose's env_file already sets these as real env vars)
_root = _find_repo_root(Path(__file__).resolve().parent)
if _root:
    load_dotenv(_root / "db.env")
# Module-specific overrides (.env next to main.py)
load_dotenv()


class Settings:
    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

    # Database (schema: mrbloop_db, hosted in mrbloop_container)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "mrbloop")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "mrbloop_db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 5))

    # Birthday feature
    BIRTHDAY_CHANNEL_NAME: str = os.getenv("BIRTHDAY_CHANNEL_NAME", "general")


settings = Settings()
