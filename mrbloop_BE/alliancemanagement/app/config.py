import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

def _find_repo_root(start: Path, marker: str = "db.env") -> Path | None:
    for directory in (start, *start.parents):
        if (directory / marker).exists():
            return directory
    return None

# Shared DB credentials from the root db.env (only relevant outside Docker;
# in Docker, docker-compose's env_file already sets these as real env vars)
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
REDEEM_SECRET   = _require('REDEEM_SECRET')
JWT_SECRET      = _require('JWT_SECRET')

# Optional variables with fallback
REDEEM_API      = _optional('REDEEM_API', 'https://kingshot-giftcode.centurygame.com/api')
ALLOWED_ORIGINS = _optional('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')

# OCR & name matching
OCR_MIN_CONFIDENCE    = float(_optional('OCR_MIN_CONFIDENCE', '0.50'))
OCR_MIN_NAME_LENGTH   = int(_optional('OCR_MIN_NAME_LENGTH', '2'))
OCR_MAX_NAME_LENGTH   = int(_optional('OCR_MAX_NAME_LENGTH', '30'))
# UI words on result screens that are never player names
OCR_IGNORE_WORDS      = {
    w.strip().casefold()
    for w in _optional(
        'OCR_IGNORE_WORDS',
        'rank,score,points,power,total,damage,kills,victory,defeat,legion,results',
    ).split(',')
    if w.strip()
}
STRIP_ALLIANCE_TAG    = _optional('STRIP_ALLIANCE_TAG', 'true').lower() == 'true'
FUZZY_MATCH_THRESHOLD = int(_optional('FUZZY_MATCH_THRESHOLD', '85'))

# Power screenshot parsing (leaderboard-style: name + power per row)
# Numbers below this are assumed to be rank/level/other columns, not power.
OCR_MIN_POWER_VALUE      = int(_optional('OCR_MIN_POWER_VALUE', '1000'))
# Row-grouping tolerance, as a fraction of the OCR'd line height, for deciding
# whether two text boxes sit on the same visual row.
OCR_ROW_Y_TOLERANCE_RATIO = float(_optional('OCR_ROW_Y_TOLERANCE_RATIO', '0.6'))

# MySQL connection settings
DB_HOST     = _optional('DB_HOST', 'localhost')
DB_PORT     = int(_optional('DB_PORT', '3306'))
DB_USER     = _require('DB_USER')
DB_PASSWORD = _require('DB_PASSWORD')
DB_NAME     = _require('DB_NAME')
