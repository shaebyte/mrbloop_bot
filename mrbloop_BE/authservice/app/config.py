import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

def _find_repo_root(start: Path, marker: str = "db.env") -> Path | None:
    for directory in (start, *start.parents):
        if (directory / marker).exists():
            return directory
    return None

# Shared DB credentials + JWT_SECRET from the root db.env (only relevant
# outside Docker; in Docker, docker-compose's env_file already sets these as
# real env vars)
_root = _find_repo_root(BASE_DIR)
if _root:
    load_dotenv(_root / "db.env")
load_dotenv(BASE_DIR / '.env')

_env = os.environ.get('APP_ENV', '').strip()
if _env:
    _override_file = BASE_DIR / f'.env.{_env}'
    if _override_file.exists():
        load_dotenv(_override_file, override=True)

def _require(key: str) -> str:
    val = os.environ.get(key, '').strip()
    if not val:
        raise RuntimeError(f"{key} is not set in .env")
    return val

def _optional(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()

# Required variables
JWT_SECRET = _require('JWT_SECRET')

# Optional variables with fallback
JWT_TTL_HOURS   = int(_optional('JWT_TTL_HOURS', '8'))
ALLOWED_ORIGINS = _optional('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')

# MySQL connection settings
DB_HOST     = _optional('DB_HOST', 'localhost')
DB_PORT     = int(_optional('DB_PORT', '3306'))
DB_USER     = _require('DB_USER')
DB_PASSWORD = _require('DB_PASSWORD')
DB_NAME     = _require('DB_NAME')
