# Database Migrations

Migrations are plain SQL files, numbered sequentially. There is no auto-runner — apply them manually before deploying the matching code.

## File naming

```
NNN_description.sql
```

- `NNN` is a zero-padded 3-digit sequence number (001, 002, …)
- Files must be applied in order

## How to apply (SQLite — dev)

```bash
sqlite3 signals.db < migrations/NNN_description.sql
```

## How to apply (PostgreSQL — production)

```bash
psql $DATABASE_URL -f migrations/NNN_description.sql
```

## Deploy checklist

When deploying a new version to the live system:

1. Check git log for any new migration files added since the last deploy
2. Apply each new migration **in order** against the live database before starting the new server process
3. If a migration fails partway through, investigate before retrying — SQLite and PostgreSQL have different transaction support for DDL

## Migration history

| # | File | What it does | Applied |
|---|------|--------------|---------|
| 001 | `001_initial_schema.sql` | Baseline schema (created by SQLAlchemy on first startup) | At project creation |
| 002 | `002_ict_fields.sql` | Adds 6 ICT columns to `trades` table for MNQ journaling | 2026-04-13 |
| 003 | `003_create_ilay_user.sql` | Seeds user `Ilay` and reassigns all trades/accounts to them | 2026-04-18 |
| 004 | `004_ict_extended_fields.sql` | Adds `ict_htf_bias`, `ict_entry_model`, `ict_pd_array` to `trades` table | 2026-04-24 |
