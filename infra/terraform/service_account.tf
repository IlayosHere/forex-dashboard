resource "google_service_account" "runtime" {
  account_id   = "forex-run-runtime"
  display_name = "Forex Dashboard — Cloud Run runtime"
  description  = "Identity used by forex-api, forex-ui, and forex-runner Cloud Run services."

  depends_on = [google_project_service.enabled]
}

resource "google_service_account" "deployer" {
  account_id   = "forex-run-deployer"
  display_name = "Forex Dashboard — GitHub Actions deployer"
  description  = "Identity assumed by GitHub Actions via Workload Identity Federation to build and deploy."

  depends_on = [google_project_service.enabled]
}
