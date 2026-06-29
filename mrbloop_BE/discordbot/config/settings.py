import os
from pathlib import Path
from dotenv import load_dotenv

# Gedeelde DB-credentials uit de root db.env
_root = Path(__file__).resolve().parents[3]
load_dotenv(_root / "db.env")
# Module-specifieke overrides (.env naast main.py)
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
    # Congrats go out at 00:15 local time of the user
    BIRTHDAY_GREET_HOUR: int = 0
    BIRTHDAY_GREET_MINUTE: int = 15
    BIRTHDAY_CHANNEL_NAME: str = os.getenv("BIRTHDAY_CHANNEL_NAME", "general")


settings = Settings()
