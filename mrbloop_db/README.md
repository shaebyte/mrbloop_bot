# mrbloop_db

Contains all MySQL schemas and migrations for the mrbloop platform.
The database is deliberately kept outside the bot so multiple applications
(bot, FE, future services) can share the same DB.

## Schemas

| Schema | Description |
|---|---|
| `mrbloop_bot` | Discord bot data (birthdays, events, giftcodes) |

## Running migrations

```bash
# One-time: create schema + user
bash migrations/000_setup.sh

# Apply every migration that hasn't run yet (tracked in schema_migrations)
bash migrate.sh
```

`migrate.sh` reads each `migrations/NNN_*.sql` file in order, skips any
filename already recorded in the `schema_migrations` table, and records new
ones as it applies them. To add a schema change, drop a new
`00X_description.sql` file in `migrations/` and re-run `migrate.sh` — no need
to track by hand what's already been applied.

## Backups

```bash
bash backup.sh
```

Dumps the database to a timestamped, gzipped file under `backups/` (git-ignored)
and deletes dumps older than 14 days. This script performs one backup+prune
cycle — schedule it yourself (cron on Linux, Task Scheduler on Windows) to run
daily, e.g.:

```cron
0 3 * * * cd /path/to/mrbloop_bot/mrbloop_db && bash backup.sh >> backup.log 2>&1
```
