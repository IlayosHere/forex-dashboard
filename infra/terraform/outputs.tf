output "api_url" {
  description = "Public URL of forex-api Cloud Run service."
  value       = google_cloud_run_v2_service.forex_api.uri
}

output "ui_url" {
  description = "Public URL of forex-ui Cloud Run service."
  value       = google_cloud_run_v2_service.forex_ui.uri
}

output "wif_provider" {
  description = "Full resource name of the Workload Identity provider for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_sa_email" {
  description = "Email of the deployer service account impersonated by GitHub Actions."
  value       = google_service_account.deployer.email
}

output "runtime_sa_email" {
  description = "Email of the Cloud Run runtime service account."
  value       = google_service_account.runtime.email
}

output "artifact_registry_repo" {
  description = "Artifact Registry docker repo base path for the forex-dashboard images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.forex.repository_id}"
}

output "cloud_sql_instance_connection_name" {
  description = "Cloud SQL instance connection name (project:region:instance)."
  value       = google_sql_database_instance.forex_db.connection_name
}

# NOTE: After `terraform apply`, seed the human-managed secrets with:
#   gcloud secrets versions add jwt_secret          --data-file=<(openssl rand -hex 32)
#   gcloud secrets versions add auth_users          --data-file=auth_users.json
#   gcloud secrets versions add discord_webhook_url --data-file=<(echo -n "$URL")
# The `database_url` and `db_password` secrets are populated by Terraform.
