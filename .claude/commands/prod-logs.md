---
description: Tail recent Cloud Run logs for a service (api, runner, or ui)
---

You are fetching recent logs from a Cloud Run service.

## Environment constants

```
GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
PROJECT="project-2f1c7228-98f9-4373-a13"
REGION="europe-west1"
```

## Service mapping

| Arg      | Cloud Run service |
|----------|-------------------|
| `api`    | `forex-api`       |
| `runner` | `forex-runner`    |
| `ui`     | `forex-ui`        |

## Arguments

`$ARGUMENTS` format: `<service> [limit]`

Examples:
```
/prod-logs runner        → last 50 lines of forex-runner
/prod-logs api 100       → last 100 lines of forex-api
/prod-logs runner 20     → last 20 lines of forex-runner
/prod-logs ui             → last 50 lines of forex-ui
```

Parse `$ARGUMENTS`:
- First word = service name (required). Must be one of: `api`, `runner`, `ui`.
- Second word = line limit (optional, default 50).

If no service is provided, print usage and exit.

## Step 1: Validate arguments

If the service arg is not `api`, `runner`, or `ui`, print:
```
Unknown service "<arg>". Use one of: api, runner, ui
```
And exit.

## Step 2: Fetch logs

```bash
"$GCLOUD" run services logs read "forex-$SERVICE" \
  --region="$REGION" --project="$PROJECT" --limit=$LIMIT
```

## Step 3: Print results

Print the raw log output. If it's empty, print:
```
No logs found for forex-$SERVICE in the last hour.
```

## Common patterns to look for

When the user asks you to check logs, highlight these if present:
- `ERROR` or `Exception` — something broke
- `scan() raised` — strategy scanner crashed
- `No data returned` — TradingView fetch failed
- `Duplicate signal skipped` — normal, but high volume may indicate a bug
- `CandleCache failed` — candle fetch issue
- `rate-limited (429)` — TradingView throttling

## Safety rules

- This is a read-only operation — no mutations.
- gcloud binary is the full `.cmd` path — never bare `gcloud`.
- Always use `--region` and `--project` flags.
