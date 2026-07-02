# Alliance Management Backend

FastAPI backend for alliance member management, screenshot-based event
attendance (OCR, in-memory — screenshots are never stored) and attendance
statistics. Part of the mrbloop monorepo: it shares the MySQL instance
(`am_*` tables) and the root `db.env` with the other back-ends.

## Setup

1. Apply the migration: `mysql -u root -p < mrbloop_db/migrations/003_alliancemanagement_initial.sql`
   (in Docker this happens automatically on first startup of the mysql container).
2. `cp .env.example .env` and fill in `REDEEM_SECRET`. DB credentials come
   from the root `db.env`. **Never commit `.env`** (already in `.gitignore`).
3. From the repo root: `docker compose up --build alliancemanagement`
4. API docs: http://localhost:8010/docs

Local development without Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Workflow

**Members** — `POST /members` with `player_id`, `alias`, `alliance_name`.
The backend logs in against the Century Game API (same signing as
redeemer.py) and fills `ingame_name` + `server` automatically. Full CRUD
available; alias is tied to the `player_id` and survives in-game renames.

**Update button** — `POST /members/refresh-names` starts a background job
that re-fetches every member's current in-game name (sequential, with
delays/backoff because of API rate limits). Poll
`GET /members/refresh-names/status` for progress. Name changes close the
open row in `am_member_name_history` and open a new one.

**Attendance** — two steps:

1. `POST /attendance/preview` (multipart): screenshots + `event_type` +
   `legion` + `event_date`. OCR runs in-memory, names are matched against
   current names AND history names valid on the event date, with fuzzy
   fallback. Returns matches (with method/score), unmatched OCR lines and
   members that were not found — review this in the frontend.
2. `POST /attendance/confirm`: the corrected list of `player_id`s. The
   event is upserted and attendance written. The database UNIQUE key
   `(player_id, event_type, event_date)` enforces one legion per event per
   date; conflicts are reported in the response instead of failing.

**Statistics** — `GET /stats/attendance` (filters: `event_type`,
`legion`, `date_from`, `date_to`, `alliance_name`) shows attended/total per
member, including 0-attendance members. `GET /stats/members/{player_id}`
gives one member's full history.

## Project layout

```
app/
├── main.py            # FastAPI app, CORS, routers; creates the DB pool at startup
├── config.py          # all settings from db.env + .env (same style as autoredeemgifts)
├── database.py        # aiomysql pool (same as discordbot core/db.py)
├── repository.py      # ALL SQL queries (same style as the discordbot repositories)
├── constants.py       # EVENT_TYPES / LEGIONS tuples (match the DB ENUMs)
├── api/               # thin routers: validate input, call repository, return dicts
│   ├── members.py     # CRUD + refresh job + name history
│   ├── events.py      # events, attendees, manual corrections
│   ├── attendance.py  # preview + confirm
│   └── stats.py
└── services/          # business logic
    ├── player_api.py  # Century Game login/sign (mirrors redeemer.py)
    ├── name_sync.py   # bulk refresh + history bookkeeping
    ├── ocr.py         # RapidOCR, in-memory
    └── matching.py    # normalize + exact/history/fuzzy matching (pure)
```

## Tuning

OCR/matching behaviour is configurable via `.env`:
`FUZZY_MATCH_THRESHOLD` (raise if you get false positives, lower if members
are missed), `OCR_MIN_CONFIDENCE`, `OCR_IGNORE_WORDS` (UI words on the result
screen), `STRIP_ALLIANCE_TAG` (strips a leading `[TAG]` from OCR lines).
