---
description: Apply SQL migrations / sync data between local SQLite and Cloud SQL Postgres
---

You are running DB migrations and data syncs for the forex dashboard between
local dev (`signals.db`, SQLite) and production (Cloud SQL Postgres).

## Context

| | Dev | Prod |
|-|-----|------|
| Engine | SQLite | PostgreSQL 16 (Cloud SQL) |
| Location | `signals.db` at repo root | Instance `forex-db`, db `forex`, user `forex` in project `project-2f1c7228-98f9-4373-a13`, region `europe-west1` |
| Connection name | — | `project-2f1c7228-98f9-4373-a13:europe-west1:forex-db` (from `terraform output cloud_sql_instance_connection_name`) |
| Access | direct file | Cloud SQL Auth Proxy on `127.0.0.1:5432` |
| Password | — | Secret Manager `db_password` → `gcloud secrets versions access latest --secret=db_password` |

Cloud SQL has `ipv4_enabled=false` (private IP only). From a laptop the **only**
supported path is the Cloud SQL Auth Proxy — do not try to open public IPs.

Migrations live in `migrations/NNN_name.sql`, numbered, one-way, applied manually.
`migrations/README.md` is the changelog.

## Prerequisites (one-time)

```bash
# gcloud + cloud-sql-proxy
gcloud auth login
gcloud config set project project-2f1c7228-98f9-4373-a13
# Install proxy: https://cloud.google.com/sql/docs/postgres/sql-proxy#install
```

## Arguments — `$ARGUMENTS` decides the mode

| Arg                       | What to do |
|---------------------------|------------|
| `new <slug>`              | Scaffold `migrations/NNN_<slug>.sql` (next number), add a row to `migrations/README.md` |
| `apply dev [file]`        | Apply one migration (or all unapplied, latest-last) to `signals.db` |
| `apply prod [file]`       | Same, but against Cloud SQL via the proxy |
| `apply both [file]`       | Dev first, then prod (only if dev succeeded) |
| `dump prod`               | `pg_dump` prod to `backups/prod_YYYYMMDD_HHMMSS.sql` |
| `dump dev`                | Copy `signals.db` → `backups/dev_YYYYMMDD_HHMMSS.db` |
| `pull prod`               | Dump prod, restore into a fresh local `signals.db.from_prod` (do not overwrite `signals.db` without asking) |
| `push dev-to-prod`        | DANGEROUS. Requires explicit user confirmation. Dump dev to a Postgres-compatible SQL, verify schema matches, apply into prod. |
| `status`                  | Show which migration files exist vs the last-applied row in `migrations/README.md` |

Default if no arg: show this menu and `status`.

## How to connect to prod (every command needing prod)

```bash
# Start the proxy in the background; kill it when done.
cloud-sql-proxy project-2f1c7228-98f9-4373-a13:europe-west1:forex-db --port 5432 &
PROXY_PID=$!
PGPASSWORD=$(gcloud secrets versions access latest --secret=db_password)
export PGPASSWORD
PG_URL="postgresql://forex@127.0.0.1:5432/forex"

# ... run psql / pg_dump here ...

kill $PROXY_PID
unset PGPASSWORD
```

Never put the DB password in command history (use `PGPASSWORD` env or `.pgpass`).
Never commit `backups/` — add it to `.gitignore` if missing.

## Applying a migration

### Dev (SQLite)
```bash
sqlite3 signals.db < migrations/NNN_name.sql
```
If the migration has a Postgres-only block (e.g. `gen_random_uuid()`), switch to
the SQLite variant that most migration files keep commented at the top, or
write a tiny Python shim with `sqlite3.connect`.

### Prod (Postgres via proxy)
```bash
psql "$PG_URL" -v ON_ERROR_STOP=1 -f migrations/NNN_name.sql
```
`ON_ERROR_STOP=1` is mandatory — otherwise psql keeps executing after a failed
statement and leaves the DB half-migrated.

## After applying

1. Update the "Applied" column in `migrations/README.md` to today's date (YYYY-MM-DD).
2. Commit both the `.sql` file and the README row in the same commit.
3. If the migration changes the user/ownership model, also update the
   `AUTH_USERS` Secret Manager secret so the startup seeder keeps the data in sync:
   ```bash
   gcloud secrets versions add auth_users --data-file=auth_users.json
   ```
4. Restart the api service if the migration changed columns referenced by ORM models:
   ```bash
   gcloud run services update forex-api --region=europe-west1 --clear-env-vars ... # or just re-deploy
   ```

## Safety rules — non-negotiable

- **Never** run `push dev-to-prod` without asking the user to confirm — it
  overwrites live data. Always `dump prod` first and print the backup path.
- **Never** `DROP` or `TRUNCATE` in prod without the user typing the confirmation.
- **Never** apply an un-reviewed migration to prod — print the SQL first,
  ask the user, then apply.
- If the migration uses Postgres-only syntax, refuse to run it against SQLite
  and tell the user there's no dev equivalent.
- Always use `ON_ERROR_STOP=1` with psql. Never use `--quiet` on prod.
- Cloud SQL has `deletion_protection=true`. Don't try to drop the instance.
- Backups dir (`backups/`) must be gitignored. If not, add it before dumping.

## Typical flows

### "I added migration 003 — apply it everywhere"
```
/db-migrate apply both 003_create_ilay_user.sql
```
→ applies to `signals.db`, then (on success) starts the proxy, applies to
Cloud SQL, stops the proxy, updates README.

### "Pull prod data locally to debug"
```
/db-migrate pull prod
```
→ `pg_dump` the prod DB to `backups/prod_<ts>.sql`, convert to sqlite with
`pgloader` **or** load into a local postgres container (preferred — prod is
Postgres, local SQLite will not round-trip). Write results to
`signals.db.from_prod`.

### "Something blew up in prod — give me a backup fast"
```
/db-migrate dump prod
```
→ `pg_dump` → `backups/prod_<ts>.sql`, print the size and path.

## Output format

At the end of every run, print:
1. What was applied (file list)
2. Where it was applied (dev / prod / both)
3. Any errors encountered
4. Next steps (commit, restart service, update secret)
