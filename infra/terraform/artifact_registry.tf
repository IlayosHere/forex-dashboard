resource "google_artifact_registry_repository" "forex" {
  location      = var.region
  repository_id = "forex"
  description   = "Docker images for the forex-dashboard (api, ui, runner)."
  format        = "DOCKER"
  labels        = local.common_labels

  depends_on = [google_project_service.enabled]
}
