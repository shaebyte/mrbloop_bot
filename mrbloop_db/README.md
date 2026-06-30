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
mysql -u root -p < migrations/000_setup.sql

# Bot schema
mysql -u root -p < migrations/001_bot_initial.sql
```
