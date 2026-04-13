resource "google_cloud_run_v2_service" "forex_ui" {
  name     = local.ui_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  labels   = local.common_labels

  template {
    service_account = google_service_account.runtime.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      # Placeholder — real image is pushed by GitHub Actions with the
      # NEXT_PUBLIC_API_URL build arg baked in.
      image = "gcr.io/cloudrun/hello"

      ports {
        container_port = 3000
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.enabled,
    google_project_iam_member.runtime,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "forex_ui_public" {
  project  = google_cloud_run_v2_service.forex_ui.project
  location = google_cloud_run_v2_service.forex_ui.location
  name     = google_cloud_run_v2_service.forex_ui.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
