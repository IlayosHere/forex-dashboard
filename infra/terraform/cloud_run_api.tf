resource "google_cloud_run_v2_service" "forex_api" {
  name     = local.api_service_name
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
      # Placeholder image — GitHub Actions rolls forward with the real image via
      # `gcloud run deploy`. lifecycle.ignore_changes below keeps Terraform from
      # fighting that rollout.
      image = "gcr.io/cloudrun/hello"

      ports {
        container_port = 8000
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.human_seeded["jwt_secret"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "AUTH_USERS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.human_seeded["auth_users"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
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
    google_secret_manager_secret_version.database_url,
    google_project_iam_member.runtime,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "forex_api_public" {
  project  = google_cloud_run_v2_service.forex_api.project
  location = google_cloud_run_v2_service.forex_api.location
  name     = google_cloud_run_v2_service.forex_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
