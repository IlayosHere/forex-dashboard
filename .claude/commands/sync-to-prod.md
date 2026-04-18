---
description: Sync local SQLite data to production Postgres with pre-flight schema check
---

You are running the full SQLite-to-Postgres data sync for the forex dashboard.
This skill handles the entire workflow: open tunnel → check schema → migrate
data → verify row counts → close tunnel. No arguments needed.

## Environment constants

```
GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
PROJECT="project-2f1c7228-98f9-4373-a13"
INSTANCE="forex-db"
CONNECTION="project-2f1c7228-98f9-4373-a13:europe-west1:forex-db"
REGION="europe-west1"
PG_HOST="127.0.0.1"
PG_PORT=5433
PG_USER="forex"
PG_DB="forex"
SQLITE_PATH="signals.db"
MIGRATE_SCRIPT="scripts/migrate_to_postgres.py"
```

Tables synced (in dependency order): `signals`, `accounts`, `trades`.
The `users` table is NOT synced — it is managed via the AUTH_USERS secret.

## Full workflow — run all steps in order

### Step 1: Open prod connection

```bash
GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
PROJECT="project-2f1c7228-98f9-4373-a13"
INSTANCE="forex-db"
CONNECTION="project-2f1c7228-98f9-4373-a13:europe-west1:forex-db"

# Enable public IP (private IP is unreachable from a laptop)
"$GCLOUD" sql instances patch "$INSTANCE" --assign-ip --project="$PROJECT" --quiet

# Authorize current IP
MY_IP=$(curl -s https://ifconfig.me)
"$GCLOUD" sql instances patch "$INSTANCE" \
  --authorized-networks="$MY_IP/32" --project="$PROJECT" --quiet

# Kill any stale proxy
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"

# Start proxy (PowerShell Start-Process — bash & dies between tool calls)
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

# Verify proxy started
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stdout.log\""
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stderr.log\" -ErrorAction SilentlyContinue"

# Fetch password
DB_PASSWORD=$("$GCLOUD" secrets versions access latest \
  --secret=db_password --project="$PROJECT")
export DB_PASSWORD
echo "Prod connection open."
```

If the proxy stderr contains "instance does not have IP of type PUBLIC", the
patch hasn't propagated — wait 10 seconds and re-run Steps 3–4.

### Step 2: Pre-flight schema check

Compare SQLite columns vs Postgres columns for each table. For any column in
SQLite but missing in Postgres, run `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

This prevents the "column does not exist" error that occurs when prod schema is
behind dev (e.g. missed a migration).

```python
import sqlite3, psycopg2, os

TABLES = ["signals", "accounts", "trades"]

# SQLite type -> Postgres type
TYPE_MAP = {
    "TEXT": "TEXT", "VARCHAR": "TEXT", "CHAR": "TEXT",
    "INTEGER": "INTEGER", "INT": "INTEGER",
    "REAL": "DOUBLE PRECISION", "FLOAT": "DOUBLE PRECISION", "NUMERIC": "DOUBLE PRECISION",
    "BOOLEAN": "BOOLEAN", "BOOL": "BOOLEAN",
    "DATETIME": "TIMESTAMP WITH TIME ZONE", "TIMESTAMP": "TIMESTAMP WITH TIME ZONE",
    "JSON": "JSONB", "BLOB": "BYTEA",
}

def to_pg_type(sqlite_type):
    upper = (sqlite_type or "TEXT").upper()
    for k, v in TYPE_MAP.items():
        if k in upper:
            return v
    return "TEXT"

src = sqlite3.connect("signals.db")
pg = psycopg2.connect(host="127.0.0.1", port=5433, user="forex",
                      password=os.environ["DB_PASSWORD"], dbname="forex")
pg.autocommit = True
cur = pg.cursor()

schema_changes = []
for table in TABLES:
    sqlite_cols = {row[1]: row[2]
                   for row in src.execute(f'PRAGMA table_info("{table}")').fetchall()}
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s""", (table,))
    pg_cols = {r[0] for r in cur.fetchall()}

    missing = set(sqlite_cols) - pg_cols
    if missing:
        for col in sorted(missing):
            pg_type = to_pg_type(sqlite_cols[col])
            sql = f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{col}" {pg_type}'
            cur.execute(sql)
            schema_changes.append(f"{table}.{col} ({pg_type})")
            print(f"  Added: {sql}")
    else:
        print(f"  {table}: schema OK")

src.close()
pg.close()
if schema_changes:
    print(f"\nSchema fixes applied: {schema_changes}")
else:
    print("\nNo schema fixes needed.")
```

### Step 3: Run the migration script

```bash
DB_PASSWORD="$DB_PASSWORD" python scripts/migrate_to_postgres.py
```

The script uses upsert (`ON CONFLICT DO UPDATE`) so re-running is always safe.
It migrates: signals (by `uq_signal_dedup` constraint), accounts and trades (by `id`).

If the script fails, print the full error, then proceed immediately to Step 5
(close connection) before stopping.

### Step 4: Verify row counts

```python
import sqlite3, psycopg2, os

TABLES = ["signals", "accounts", "trades"]
src = sqlite3.connect("signals.db")
pg = psycopg2.connect(host="127.0.0.1", port=5433, user="forex",
                      password=os.environ["DB_PASSWORD"], dbname="forex")
cur = pg.cursor()

print(f"\n{'Table':<12} {'SQLite':>8} {'Prod':>8}  Match")
print("-" * 38)
all_ok = True
for table in TABLES:
    sq = src.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
    cur.execute(f'SELECT count(*) FROM "{table}"')
    pg_count = cur.fetchone()[0]
    ok = sq <= pg_count
    if not ok:
        all_ok = False
    print(f"{table:<12} {sq:>8} {pg_count:>8}  {'OK' if ok else 'MISMATCH'}")

src.close()
pg.close()
if not all_ok:
    print("\nWARNING: row count mismatch — investigate before proceeding.")
```

### Step 5: Close prod connection

Always run this, even if earlier steps failed.

```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
"$GCLOUD" sql instances patch "$INSTANCE" --no-assign-ip --project="$PROJECT" --quiet
echo "Prod connection closed. Public IP disabled."
```

### Step 6: Ask about API restart

Print this and wait for the user's answer before doing anything:

```
Sync complete. Restart the forex-api Cloud Run service?
(Picks up new data and clears in-memory state like rate limiters.)
Type yes to restart, no to skip.
```

If yes:
```bash
IMAGE=$("$GCLOUD" run services describe forex-api \
  --region="$REGION" --project="$PROJECT" \
  --format="value(template.containers[0].image)")
"$GCLOUD" run deploy forex-api --image="$IMAGE" \
  --region="$REGION" --project="$PROJECT" --quiet
echo "forex-api redeployed."
```

Do NOT restart automatically — always ask first.

## Output summary

Print at the end:

```
SYNC COMPLETE
  Schema fixes:  [columns added, or "none"]
  Rows migrated: signals=N, accounts=N, trades=N
  Row counts:    [OK / MISMATCH per table]
  Connection:    closed (public IP disabled)
  API restart:   [yes / no / skipped]
```

## Safety rules

- The `users` table is never synced — password hashes are managed via AUTH_USERS secret.
- Upsert is idempotent — re-running this skill is always safe.
- Always run Step 5 (close connection), even on failure.
- Port is **5433**, never 5432.
- gcloud binary is `gcloud.cmd` at full path — never bare `gcloud`.
