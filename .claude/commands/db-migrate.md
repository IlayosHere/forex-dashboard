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
| Connection name | — | `project-2f1c7228-98f9-4373-a13:europe-west1:forex-db` |
| Access | direct file | Cloud SQL Auth Proxy on `127.0.0.1:5433` (port **5433** — not 5432, which conflicts with local Postgres) |
| Password | — | Secret Manager secret `db_password` |

This project is worked on from both a Mac and a Windows machine. gcloud binary
and proxy binary paths differ by OS — see OS detection below. Neither is on
PATH on either machine, so always use the resolved `$GCLOUD`/`$PROXY` vars,
never bare `gcloud` or a bare proxy invocation.

Cloud SQL `forex-db` has only public IP — no private IP/PSC — so it's always
reachable from a laptop via the proxy, no enable/disable step needed. See "How
to connect to prod" and the "Public IP is permanently enabled" note in
`/prod-connect` for why.

`psql` and `pg_dump` are **not installed** on either machine. All Postgres
interaction must go through Python (psycopg2) or `scripts/migrate_to_postgres.py`.

Migrations live in `migrations/NNN_name.sql`, numbered, one-way, applied manually.
`migrations/README.md` is the changelog.

## OS detection — run this first, every time

```bash
UNAME=$(uname -s 2>/dev/null || echo "Unknown")
if [ "$UNAME" = "Darwin" ]; then
  PLATFORM="mac"
  GCLOUD="/opt/homebrew/bin/gcloud"
  PROXY="scripts/cloud-sql-proxy.darwin.arm64"
else
  PLATFORM="windows"
  GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
  PROXY="scripts/cloud-sql-proxy.exe"
fi
```

## Environment constants (same on both platforms)

```
PROJECT="project-2f1c7228-98f9-4373-a13"
INSTANCE="forex-db"
CONNECTION="project-2f1c7228-98f9-4373-a13:europe-west1:forex-db"
REGION="europe-west1"
PG_HOST="127.0.0.1"
PG_PORT=5433
PG_USER="forex"
PG_DB="forex"
```

## Prerequisites (one-time setup, per machine)

Both of these must be run at least once **on each machine you work from** —
auth does not carry over between Mac and Windows. `auth login` is for gcloud
commands; `application-default login` is for the proxy (ADC).

```bash
"$GCLOUD" auth login
"$GCLOUD" auth application-default login
"$GCLOUD" config set project "$PROJECT"
# Verify proxy binary exists
ls "$PROXY"
```

On Mac, gcloud is installed via `brew install --cask google-cloud-sdk`, and the
proxy binary is downloaded directly from Google (not in Homebrew):
```bash
curl -L -o scripts/cloud-sql-proxy.darwin.arm64 \
  "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.22.1/cloud-sql-proxy.darwin.arm64"
chmod +x scripts/cloud-sql-proxy.darwin.arm64
```
(For Intel Macs, substitute `darwin.amd64` for `darwin.arm64` in both the
filename and the download URL.)

## Arguments — `$ARGUMENTS` decides the mode

| Arg                       | What to do |
|---------------------------|------------|
| `new <slug>`              | Scaffold `migrations/NNN_<slug>.sql` (next number), add a row to `migrations/README.md` |
| `apply dev [file]`        | Apply one migration (or all unapplied, latest-last) to `signals.db` |
| `apply prod [file]`       | Same, but against Cloud SQL via the proxy (uses Python, not psql) |
| `apply both [file]`       | Dev first, then prod (only if dev succeeded) |
| `dump dev`                | Copy `signals.db` to `backups/dev_YYYYMMDD_HHMMSS.db` |
| `dump prod`               | Dump prod tables to `backups/prod_YYYYMMDD_HHMMSS.sql` via Python (no pg_dump) |
| `pull prod`               | Dump prod, write to `signals.db.from_prod` (do not overwrite `signals.db` without asking) |
| `push dev-to-prod`        | DANGEROUS. Requires explicit user confirmation. Uses `scripts/migrate_to_postgres.py`. Always `dump prod` first. |
| `status`                  | Show which migration files exist vs the last-applied row in `migrations/README.md` |

Default if no arg: show this menu and `status`.

## How to connect to prod

Public IP is **permanently enabled** on `forex-db` — no private IP/PSC exists
as a fallback (Terraform-declared: `infra/terraform/cloud_sql.tf`,
`ipv4_enabled = true`, `authorized_networks = 0.0.0.0/0`, relying on SSL).
There's no enable/disable dance anymore — never run `--assign-ip`,
`--no-assign-ip`, or change `--authorized-networks`. Just start the proxy.

Plain bash background jobs (`&`) die between Claude tool calls. The proxy must
be launched detached at the OS level so it survives across calls — `nohup` +
`disown` on Mac, PowerShell `Start-Process` on Windows. Run the OS detection
block first (above) to set `$GCLOUD`/`$PROXY`, then:

```bash
PROJECT="project-2f1c7228-98f9-4373-a13"
INSTANCE="forex-db"
CONNECTION="project-2f1c7228-98f9-4373-a13:europe-west1:forex-db"
```

**Mac** — start the proxy:
```bash
pkill -f "cloud-sql-proxy.darwin.arm64" 2>/dev/null; true
nohup "$PROXY" "$CONNECTION" --port 5433 \
  > /tmp/cloud-sql-proxy-stdout.log 2> /tmp/cloud-sql-proxy-stderr.log < /dev/null &
disown
sleep 5
cat /tmp/cloud-sql-proxy-stdout.log
cat /tmp/cloud-sql-proxy-stderr.log 2>/dev/null
```

**Windows** — start the proxy:
```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
powershell.exe -Command "
\$outlog = \"\$env:TEMP\proxy-stdout.log\"
\$errlog = \"\$env:TEMP\proxy-stderr.log\"
Remove-Item \$outlog, \$errlog -ErrorAction SilentlyContinue
Start-Process -FilePath 'scripts/cloud-sql-proxy.exe' \
  -ArgumentList '$CONNECTION --port 5433' \
  -RedirectStandardOutput \$outlog \
  -RedirectStandardError \$errlog \
  -WindowStyle Hidden"
sleep 5
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stdout.log\""
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stderr.log\" -ErrorAction SilentlyContinue"
```

```bash
# Fetch password (same on both platforms)
DB_PASSWORD=$("$GCLOUD" secrets versions access latest \
  --secret=db_password --project="$PROJECT")
export DB_PASSWORD
```

When done with prod, only the proxy needs killing:

**Mac:**
```bash
pkill -f "cloud-sql-proxy.darwin.arm64" 2>/dev/null; true
```

**Windows:**
```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
```

Never put the DB password in command history.
Never commit `backups/` — add it to `.gitignore` if missing.

## Applying a migration

### Dev (SQLite — use Python, not sqlite3 CLI)

```python
import sqlite3
conn = sqlite3.connect("signals.db")
with open("migrations/NNN_name.sql") as f:
    conn.executescript(f.read())
conn.close()
print("Migration applied to dev.")
```

If the migration has Postgres-only syntax (e.g. `gen_random_uuid()`), use the
SQLite variant that migration files keep commented at the top.

### Prod (Postgres via proxy — Python, not psql)

Always print the SQL first and ask the user to confirm before applying.

```python
import psycopg2, os

password = os.environ["DB_PASSWORD"]
conn = psycopg2.connect(host="127.0.0.1", port=5433, user="forex",
                        password=password, dbname="forex")
conn.autocommit = True
with open("migrations/NNN_name.sql") as f:
    sql = f.read()

print("=== SQL TO APPLY ===")
print(sql)
print("===================")
# Ask user to confirm, then:
conn.cursor().execute(sql)
conn.close()
print("Migration applied to prod.")
```

### Dumping prod (Python, no pg_dump)

```python
import psycopg2, os
from datetime import datetime

conn = psycopg2.connect(host="127.0.0.1", port=5433, user="forex",
                        password=os.environ["DB_PASSWORD"], dbname="forex")
cur = conn.cursor()
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
path = f"backups/prod_{ts}.sql"

cur.execute("""SELECT table_name FROM information_schema.tables
               WHERE table_schema='public' ORDER BY table_name""")
tables = [r[0] for r in cur.fetchall()]

with open(path, "w") as f:
    for table in tables:
        cur.execute(f'SELECT * FROM "{table}"')
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        f.write(f"-- TABLE: {table} ({len(rows)} rows)\n")
        for row in rows:
            vals = ", ".join(repr(v) for v in row)
            f.write(f"INSERT INTO \"{table}\" ({', '.join(cols)}) VALUES ({vals});\n")

conn.close()
print(f"Dump written to {path}")
```

## After applying

1. Update the "Applied" column in `migrations/README.md` to today's date (YYYY-MM-DD).
2. Commit both the `.sql` file and the README row in the same commit.
3. If the migration changes the user/ownership model, also update the `AUTH_USERS` secret:
   ```bash
   "$GCLOUD" secrets versions add auth_users --data-file=auth_users.json --project="$PROJECT"
   ```
4. Restart the API if the migration changed columns referenced by ORM models:
   ```bash
   # Get current image and redeploy
   IMAGE=$("$GCLOUD" run services describe forex-api --region=europe-west1 \
     --project="$PROJECT" --format="value(template.containers[0].image)")
   "$GCLOUD" run deploy forex-api --image="$IMAGE" --region=europe-west1 \
     --project="$PROJECT" --quiet
   ```

## Safety rules — non-negotiable

- **Never** run `push dev-to-prod` without asking the user to confirm — it
  overwrites live data. Always `dump prod` first and print the backup path.
- **Never** `DROP` or `TRUNCATE` in prod without the user typing the confirmation.
- **Never** apply an un-reviewed migration to prod — print the SQL first, ask the user, then apply.
- If the migration uses Postgres-only syntax, refuse to run it against SQLite and tell the user.
- Cloud SQL has `deletion_protection=true`. Don't try to drop the instance.
- Backups dir (`backups/`) must be gitignored. Check before dumping.
- Port is **5433**, not 5432.
- Always close the prod connection when done (kill the proxy — public IP
  itself stays permanently enabled, never try to disable it).

## Typical flows

### "Apply migration 003 to both"
```
/db-migrate apply both 003_create_ilay_user.sql
```
→ applies Python-based migration to `signals.db`, then opens prod tunnel,
applies to Cloud SQL, closes tunnel, updates README.

### "Pull prod data locally to debug"
```
/db-migrate pull prod
```
→ dumps prod via Python to `backups/prod_<ts>.sql`, writes table data to
`signals.db.from_prod` (does NOT overwrite `signals.db`).

### "Something blew up in prod — give me a backup fast"
```
/db-migrate dump prod
```
→ dumps all tables to `backups/prod_<ts>.sql` via psycopg2, prints size and path.

## Output format

At the end of every run, print:
1. What was applied (file list)
2. Where it was applied (dev / prod / both)
3. Any errors encountered
4. Next steps (commit, restart service, update secret)
5. Whether the prod connection is still open (remind user to close if so)
