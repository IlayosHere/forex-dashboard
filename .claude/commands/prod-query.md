---
description: Run a read-only SQL query against the production Postgres database
---

You are running a read-only SQL query against the production database.

## Environment constants

```
GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
PROJECT="project-2f1c7228-98f9-4373-a13"
INSTANCE="forex-db"
CONNECTION="project-2f1c7228-98f9-4373-a13:europe-west1:forex-db"
PG_HOST="127.0.0.1"
PG_PORT=5433
PG_USER="forex"
PG_DB="forex"
```

## What this skill does

1. Opens the prod tunnel (reuses `/prod-connect open` steps)
2. Runs the SQL query from `$ARGUMENTS`
3. Prints the results
4. Closes the tunnel

If the tunnel is already open (port 5433 responding), skip straight to step 2.

## Arguments

`$ARGUMENTS` is the SQL query to run. Examples:

```
/prod-query SELECT count(*) FROM signals WHERE resolution IS NULL
/prod-query SELECT strategy, count(*) FROM signals GROUP BY strategy
/prod-query SELECT id, symbol, candle_time FROM signals ORDER BY candle_time DESC LIMIT 5
```

If `$ARGUMENTS` is empty, print usage and exit.

## Safety rules

- **READ-ONLY**: Never run INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or
  any mutating statement. If the query contains a mutating keyword, refuse and
  print a warning. This skill is strictly for SELECT queries.
- Always close the tunnel when done (unless it was already open before).
- Port is **5433**, never 5432.
- gcloud binary is the full `.cmd` path — never bare `gcloud`.

## Step 1: Check if tunnel is already open

```bash
python - <<'EOF'
import socket
try:
    s = socket.create_connection(("127.0.0.1", 5433), timeout=2)
    s.close()
    print("TUNNEL_OPEN")
except Exception:
    print("TUNNEL_CLOSED")
EOF
```

If `TUNNEL_OPEN`, set a flag to NOT close the tunnel at the end — the user
opened it manually and may want it to stay open.

If `TUNNEL_CLOSED`, open the tunnel using the same steps as `/prod-connect open`:

### 1a. Enable public IP

```bash
"$GCLOUD" sql instances patch "$INSTANCE" --assign-ip --project="$PROJECT" --quiet
```

### 1b. Authorize current IP

```bash
MY_IP=$(curl -s https://ifconfig.me)
"$GCLOUD" sql instances patch "$INSTANCE" \
  --authorized-networks="$MY_IP/32" --project="$PROJECT" --quiet
```

### 1c. Kill stale proxy, start fresh

```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
```

```bash
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
```

### 1d. Verify proxy

```bash
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stdout.log\""
```

Must contain "The proxy has started successfully".

## Step 2: Run the query

```bash
DB_PASSWORD=$("$GCLOUD" secrets versions access latest \
  --secret=db_password --project="$PROJECT")
export DB_PASSWORD

python - <<'PYEOF'
import os, psycopg2, sys

sql = """$ARGUMENTS"""

# Safety: refuse mutating queries
MUTATING = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
first_word = sql.strip().split()[0].upper() if sql.strip() else ""
if first_word in MUTATING:
    print(f"REFUSED: {first_word} queries are not allowed via /prod-query")
    sys.exit(1)

conn = psycopg2.connect(
    host="127.0.0.1", port=5433, user="forex",
    password=os.environ["DB_PASSWORD"], dbname="forex",
)
conn.set_session(readonly=True)
cur = conn.cursor()
cur.execute(sql)

if cur.description:
    headers = [d[0] for d in cur.description]
    rows = cur.fetchall()
    # Print as aligned table
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    print(f"\n({len(rows)} row(s))")
else:
    print("Query executed (no results)")

conn.close()
PYEOF
```

## Step 3: Close tunnel (if we opened it)

Only if the tunnel was CLOSED before we started:

```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
"$GCLOUD" sql instances patch "$INSTANCE" --no-assign-ip --project="$PROJECT" --quiet
echo "Tunnel closed."
```

If the tunnel was already open, print:
```
Tunnel was already open — leaving it open. Run /prod-connect close when done.
```
