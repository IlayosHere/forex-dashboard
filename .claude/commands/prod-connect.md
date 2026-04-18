---
description: Open/close a secure tunnel to the production Cloud SQL database
---

You are managing the production database tunnel for the forex dashboard.

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
```

## Arguments — `$ARGUMENTS` decides the mode

| Arg      | What to do |
|----------|------------|
| `open`   | Enable public IP, authorize current IP, start proxy, verify connection |
| `close`  | Kill proxy, remove authorized networks, disable public IP |
| `status` | Check if proxy is running and can connect |

Default if no arg: `status`.

## `open` — Establish prod tunnel

Run these steps in order. Stop and report if any step fails.

### Step 1: Enable public IP

Cloud SQL has `ipv4_enabled=false` (private IP only: `10.41.216.3`). The proxy
cannot reach the private IP from a laptop. Must temporarily enable public IP.

```bash
"$GCLOUD" sql instances patch "$INSTANCE" --assign-ip --project="$PROJECT" --quiet
```

### Step 2: Authorize current public IP

```bash
MY_IP=$(curl -s https://ifconfig.me)
"$GCLOUD" sql instances patch "$INSTANCE" \
  --authorized-networks="$MY_IP/32" --project="$PROJECT" --quiet
echo "Authorized IP: $MY_IP"
```

### Step 3: Kill any stale proxy process

```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
```

### Step 4: Start proxy via PowerShell Start-Process

Bash background jobs (`&`) die between Claude tool calls. PowerShell
`Start-Process` launches a fully detached process that survives.

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

### Step 5: Verify proxy started successfully

```bash
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stdout.log\""
powershell.exe -Command "Get-Content \"\$env:TEMP\proxy-stderr.log\" -ErrorAction SilentlyContinue"
```

The stdout log should contain:
```
The proxy has started successfully and is ready for new connections!
```

If stderr contains "Config error: instance does not have IP of type PUBLIC",
the public IP patch hasn't propagated yet — wait 10 seconds and retry Steps 3–4.

If stderr contains "could not find default credentials", run:
```bash
"$GCLOUD" auth application-default login
```
Then retry.

### Step 6: Verify database connection

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

### Step 7: Print success

```
PROD TUNNEL OPEN
  Host:     127.0.0.1:5433
  Database: forex / user: forex
  Password: in env var DB_PASSWORD

  WARNING: Public IP is now enabled on the Cloud SQL instance.
  Run /prod-connect close when you are done.
```

## `close` — Tear down prod tunnel

### Step 1: Kill proxy

```bash
powershell.exe -Command "Get-Process cloud-sql-proxy -ErrorAction SilentlyContinue | Stop-Process -Force"
```

### Step 2: Disable public IP

```bash
"$GCLOUD" sql instances patch "$INSTANCE" --no-assign-ip --project="$PROJECT" --quiet
echo "PROD TUNNEL CLOSED — proxy stopped, public IP disabled."
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

Check Cloud SQL public IP status:
```bash
"$GCLOUD" sql instances describe "$INSTANCE" --project="$PROJECT" \
  --format="value(settings.ipConfiguration.ipv4Enabled)"
```

## Safety rules

- Always warn that public IP is enabled after `open` and remind to `close`.
- Always run `close` when finished — never leave public IP enabled.
- Port is **5433**, never 5432.
- gcloud binary is the full `.cmd` path — never bare `gcloud`.
- Both `gcloud auth login` and `gcloud auth application-default login` must
  have been run at least once before first use. They are separate.
