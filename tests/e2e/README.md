# E2E Test Suite

End-to-end tests that run against a deployed Cloud Run environment.
Kept separate from `tests/*` unit tests so a plain `pytest` never hits
the network. All fixtures skip themselves if env vars are missing, so
these tests are safe to collect alongside unit tests.

## Install

```bash
pip install -r tests/e2e/requirements.txt
```

## Required environment

| Var | What |
|-----|------|
| `API_URL` | Base URL of `forex-api` Cloud Run service |
| `UI_URL` | Base URL of `forex-ui` Cloud Run service |
| `E2E_USER` | Username of the dedicated test user |
| `E2E_PASSWORD` | Password for the test user |

Optional:

| Var | What |
|-----|------|
| `CORS_STRICT=true` | Opt in to the negative CORS test (fails if `CORS_ORIGINS=*`) |

## Run

```bash
# Fast suite (skips the 16-min runner check)
pytest tests/e2e/ -v

# Include the slow runner-scheduling check
pytest tests/e2e/ -v -m slow
```

The helper script wires everything up from `gcloud`:

```bash
infra/e2e/run.sh
```

## What each test proves

| Test | Proves |
|------|--------|
| `test_infra_liveness.py::test_api_docs_endpoint` | api service is reachable and serving OpenAPI UI |
| `test_infra_liveness.py::test_ui_login_page` | ui service renders the login route |
| `test_jwt_auth.py::test_login_returns_jwt` | POST /api/auth/login returns `access_token` |
| `test_jwt_auth.py::test_jwt_claims` | token `sub` matches user, `exp` in future |
| `test_jwt_auth.py::test_authorized_signals_list` | JWT grants access to a protected route |
| `test_jwt_auth.py::test_tampered_token_rejected` | signature verification is on |
| `test_jwt_auth.py::test_no_token_rejected` | anonymous access blocked |
| `test_jwt_auth.py::test_20_parallel_requests` | stateless JWT holds across multiple Cloud Run instances |
| `test_db_roundtrip.py::test_create_get_update_delete_trade` | api ↔ Cloud SQL path works for the full CRUD cycle, P&L computed on close |
| `test_cors.py::test_cors_from_ui_origin` | ui origin is allowed through CORS preflight |
| `test_cors.py::test_cors_from_evil_origin` | unknown origin is not allowed (opt-in) |
| `test_ui_render.py::test_ui_homepage_renders` | ui `/` responds 200 |
| `test_ui_render.py::test_next_public_api_url_baked` | `NEXT_PUBLIC_API_URL` build-arg was threaded into the ui image (catches the classic localhost bug) |
| `test_runner_liveness.py::test_runner_scheduling` | (slow) forex-runner is ticking and writing signals |

## Seeding the e2e user

The e2e user lives alongside real users in the `AUTH_USERS` Secret
Manager secret. `AUTH_USERS` is JSON mapping username to bcrypt hash:

```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('CHANGE_ME'))"
# copy the hash into the JSON blob below
cat > /tmp/auth_users.json <<'JSON'
{
  "alice": "$2b$12$...existing...",
  "e2e-bot": "$2b$12$...hash-from-above..."
}
JSON

gcloud secrets versions add auth_users --data-file=/tmp/auth_users.json
rm /tmp/auth_users.json
```

Then roll the api service to pick up the new secret version:

```bash
gcloud run services update forex-api --region=europe-west1
```

Set `E2E_USER=e2e-bot` and `E2E_PASSWORD=CHANGE_ME` in the environment
that runs the tests (GitHub Actions secrets, or `.env` locally).
