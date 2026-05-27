data "google_compute_network" "default" {
  name = "default"

  depends_on = [google_project_service.enabled]
}
