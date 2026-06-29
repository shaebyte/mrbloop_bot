# mrbloop_db

Bevat alle MySQL schema's en migrations voor het mrbloop platform.
De database staat bewust buiten de bot zodat meerdere applicaties
(bot, FE, toekomstige services) dezelfde DB kunnen delen.

## Schema's

| Schema | Beschrijving |
|---|---|
| `mrbloop_bot` | Discord bot data (verjaardagen, events, giftcodes) |

## Migrations uitvoeren

```bash
# Eenmalig: schema aanmaken + user
mysql -u root -p < migrations/000_setup.sql

# Bot schema
mysql -u root -p < migrations/001_bot_initial.sql
```
