#!/usr/bin/env bash
# infra/e2e/run.sh
# ----------------
# Resolve the deployed API_URL and UI_URL from `gcloud run services describe`
# and run the e2e test suite against them. E2E_USER and E2E_PASSWORD must
# already be set in the environment (they are not stored in Terraform state).
#
# Usage:
#   E2E_USER=e2e-bot E2E_PASSWORD=... infra/e2e/run.sh [extra pytest args]
set -euo pipefail

REGION="${GCP_REGION:-europe-west1}"
API_SERVICE="${API_SERVICE:-forex-api}"
UI_SERVICE="${UI_SERVICE:-forex-ui}"

: "${E2E_USER:?E2E_USER is required - set to the test user seeded in AUTH_USERS}"
: "${E2E_PASSWORD:?E2E_PASSWORD is required - matches the hash in AUTH_USERS}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "error: gcloud CLI not found on PATH" >&2
  exit 1
fi

echo "resolving Cloud Run service URLs in region ${REGION}..."
API_URL="$(gcloud run services describe "${API_SERVICE}" \
  --region="${REGION}" --format='value(status.url)')"
UI_URL="$(gcloud run services describe "${UI_SERVICE}" \
  --region="${REGION}" --format='value(status.url)')"

if [[ -z "${API_URL}" ]]; then
  echo "error: could not resolve URL for ${API_SERVICE}" >&2
  exit 1
fi
if [[ -z "${UI_URL}" ]]; then
  echo "error: could not resolve URL for ${UI_SERVICE}" >&2
  exit 1
fi

echo "API_URL=${API_URL}"
echo "UI_URL=${UI_URL}"

export API_URL UI_URL E2E_USER E2E_PASSWORD

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

exec pytest tests/e2e/ -v "$@"
