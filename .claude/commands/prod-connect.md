---
description: Open/close a secure tunnel to the production Cloud SQL database
---

You are managing the production database tunnel for the forex dashboard.

## OS detection — run this first, every time

This project is worked on from both a Mac and a Windows machine. Always detect
which one you're on before running any command below — never assume.

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
echo "Platform: $PLATFORM, gcloud: $GCLOUD, proxy: $PROXY"
```

On Mac, `gcloud` is installed via `brew install --cask google-cloud-sdk` but
`/opt/homebrew/bin` is not reliably on PATH in every shell — always use the
full `$GCLOUD` path, never bare `gcloud`, same rule as Windows.

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

## Arguments — `$ARGUMENTS` decides the mode

| Arg      | What to do |
|----------|------------|
| `open`   | Start proxy, verify connection |
| `close`  | Kill proxy |
| `status` | Check if proxy is running and can connect |

Default if no arg: `status`.

## Public IP is permanently enabled — do not toggle it

Cloud SQL instance `forex-db` has **no private IP or PSC configured at all** —
only public IP. This is declared in Terraform (`infra/terraform/cloud_sql.tf`,
`managed_by=terraform` label): `ipv4_enabled = true` with
`authorized_networks = 0.0.0.0/0` permanently, relying on `sslMode =
ENCRYPTED_ONLY` for security rather than IP allowlisting (see the comment in
that file: "Cloud Run uses dynamic IPs — allow all, SSL required for security").

This used to be different (private-IP-primary, public IP toggled on/off per
session) before the instance was destroyed and recreated during a Terraform
migration on 2026-05-27 (see CLAUDE.md "Production Data Safety" section). The
recreated instance only has public IP. Do not try to restore the old
toggle-it-off behavior:

- **Never** run `--no-assign-ip` — it now fails outright (`HTTPError 400: At
  least one of Public IP or Private IP or PSC connectivity must be enabled`),
  since there's no fallback connectivity path. If you see this error, that's
  expected — it means there's nothing to disable. Don't troubleshoot it.
- **Never** change `--authorized-networks` away from `0.0.0.0/0` — Terraform
  owns this setting and will drift-detect/revert it on the next `terraform
  apply`. If you ever find it set to something narrower (e.g. a single IP left
  over from manual debugging), restore it to `0.0.0.0/0` immediately:
  ```bash
  "$GCLOUD" sql instances patch "$INSTANCE" --authorized-networks="0.0.0.0/0" --project="$PROJECT" --quiet
  ```
- If you genuinely need to lock this down (private IP, narrower allowlist),
  that's a deliberate Terraform change to `google_sql_database_instance` —
  follow the "Production Data Safety — MANDATORY" dump-first workflow in
  CLAUDE.md before touching it, and get the user's explicit sign-off first.

## `open` — Establish prod tunnel

Run these steps in order. Stop and report if any step fails.

### Step 1: Kill any stale proxy process

**Mac:**
```bash
pkill -f "cloud-sql-proxy.darwin.arm64" 2>/dev/null; true
```

**Windows:**
```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
```

### Step 2: Start the proxy detached

Plain bash background jobs (`&`) die between Claude tool calls, so the proxy
must be launched in a way that survives — detached at the OS level, not
attached to this tool call's shell.

**Mac** — `nohup` + `disown` detaches the process from this shell the same way
`Start-Process` does on Windows:
```bash
nohup "$PROXY" "$CONNECTION" --port 5433 \
  > /tmp/cloud-sql-proxy-stdout.log 2> /tmp/cloud-sql-proxy-stderr.log < /dev/null &
disown
sleep 5
```

**Windows** — PowerShell `Start-Process` launches a fully detached process:
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

### Step 3: Verify proxy started successfully

**Mac:**
```bash
cat /tmp/cloud-sql-proxy-stdout.log
cat /tmp/cloud-sql-proxy-stderr.log 2>/dev/null
```

**Windows:**
```bash
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stdout.log\""
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stderr.log\" -ErrorAction SilentlyContinue"
```

The stdout log should contain:
```
The proxy has started successfully and is ready for new connections!
```

If stderr contains "could not find default credentials", run:
```bash
"$GCLOUD" auth application-default login
```
Then retry.

### Step 4: Verify database connection

```bash
DB_PASSWORD=$("$GCLOUD" secrets versions access latest \
  --secret=db_password --project="$PROJECT")
export DB_PASSWORD

python - <<'EOF'
import psycopg2, os
conn = psycopg2.connect(host="127.0.0.1", port=5433, user="forex",
                        password=os.environ["DB_PASSWORD"], dbname="forex")
cur = conn.cursor()
cur.execute("SELECT current_database(), current_user")
db, user = cur.fetchone()
cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
tables = cur.fetchone()[0]
print(f"Connected: {db} as {user} ({tables} tables)")
conn.close()
EOF
```

### Step 5: Print success

```
PROD TUNNEL OPEN
  Host:     127.0.0.1:5433
  Database: forex / user: forex
  Password: in env var DB_PASSWORD
```

## `close` — Tear down prod tunnel

Only the proxy needs to be stopped — public IP and authorized networks stay
as-is permanently (see "Public IP is permanently enabled" above).

**Mac:**
```bash
pkill -f "cloud-sql-proxy.darwin.arm64" 2>/dev/null; true
echo "PROD TUNNEL CLOSED — proxy stopped."
```

**Windows:**
```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
echo "PROD TUNNEL CLOSED — proxy stopped."
```

## `status` — Check tunnel health

```bash
# Check if port 5433 is accepting connections
python - <<'EOF'
import socket
try:
    s = socket.create_connection(("127.0.0.1", 5433), timeout=2)
    s.close()
    print("Port 5433: OPEN (proxy is running)")
except Exception:
    print("Port 5433: CLOSED (proxy is not running)")
EOF
```

If port is open, also test the DB connection using DB_PASSWORD from env.

## Safety rules

- Port is **5433**, never 5432.
- Always run the OS detection block first and use `$GCLOUD`/`$PROXY` — never
  bare `gcloud`, on either platform. On Mac that's `/opt/homebrew/bin/gcloud`;
  on Windows the full `gcloud.cmd` path.
- Both `gcloud auth login` and `gcloud auth application-default login` must
  have been run at least once before first use, on whichever machine you're
  on. They are separate and per-machine — auth on Windows doesn't carry over
  to Mac or vice versa.
- Never modify `--authorized-networks` or try `--no-assign-ip` — see "Public
  IP is permanently enabled" above. Only `close` needs to kill the proxy.
