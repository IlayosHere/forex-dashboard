---
description: Redeploy Cloud Run services to pick up new secrets/config and clear in-memory state
---

You are redeploying Cloud Run services for the forex dashboard. Redeploying
with the same image forces a new revision, which picks up updated Secret Manager
values and clears all in-memory state (rate limiters, caches, etc.).

## OS detection — run this first, every time

```bash
UNAME=$(uname -s 2>/dev/null || echo "Unknown")
if [ "$UNAME" = "Darwin" ]; then
  GCLOUD="/opt/homebrew/bin/gcloud"
else
  GCLOUD="C:/Users/Ilay/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
fi
```

## Environment constants (same on both platforms)

```
PROJECT="project-2f1c7228-98f9-4373-a13"
REGION="europe-west1"
API_URL="https://forex-api-hsogimk2jq-ew.a.run.app"
```

## Services

| Name           | Purpose                           |
|----------------|-----------------------------------|
| `forex-api`    | FastAPI backend                   |
| `forex-runner` | Strategy scanner / signal runner  |
| `forex-ui`     | Next.js frontend                  |

## Arguments — `$ARGUMENTS` decides scope

| Arg       | What to do |
|-----------|------------|
| `api`     | Redeploy `forex-api` only |
| `runner`  | Redeploy `forex-runner` only |
| `ui`      | Redeploy `forex-ui` only |
| `all`     | Redeploy all three in order: api → runner → ui |
| *(empty)* | Default to `api` |

## How to redeploy a service

### Step 1: Print the warning

Before deploying, always print:
```
Redeploying clears ALL in-memory state:
  - Rate limiters reset to zero
  - Cached data re-fetched from DB on next request
Proceeding...
```

### Step 2: Get the current image

Never change the image — image updates are done by CI/CD, not manually.

```bash
IMAGE=$("$GCLOUD" run services describe SERVICE_NAME \
  --region="$REGION" --project="$PROJECT" \
  --format="value(template.containers[0].image)")
echo "Image: $IMAGE"
```

### Step 3: Deploy with same image

```bash
"$GCLOUD" run deploy SERVICE_NAME \
  --image="$IMAGE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --quiet
```

This creates a new revision with 100% traffic routed to it automatically.

### Step 4: Health check (forex-api only)

For `forex-api`, verify the new revision is serving:

```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/signals")
echo "Health check: $API_URL/api/signals -> HTTP $HTTP_CODE"
```

Expected:
- **200 or 401** — healthy (401 means auth is working, endpoint exists)
- **500 or no response** — something is wrong; check logs:
  ```bash
  "$GCLOUD" run services logs read forex-api \
    --region="$REGION" --project="$PROJECT" --limit=30
  ```

For `forex-runner` and `forex-ui` there is no health check endpoint — just
confirm the deploy command exited 0.

## Sequence for `all`

Deploy in this order so the backend is ready before runner and UI start:

1. `forex-api` — deploy + health check
2. `forex-runner` — deploy
3. `forex-ui` — deploy

If any deploy fails, stop and report the error. Do not continue to the next service.

## Output format

```
DEPLOY COMPLETE
  Services:  [services deployed]
  Image:     [image tag]
  Region:    europe-west1
  Health:    [HTTP 200/401 = OK | HTTP 500 = UNHEALTHY | not checked]
```

## Safety rules

- Never change the image. Always redeploy with the image currently in use.
- Always use `--quiet` to suppress interactive prompts.
- Run the OS detection block first and use `$GCLOUD` — never bare `gcloud`,
  on either platform.
- If a deploy fails, stop immediately. Do not continue to the next service.
