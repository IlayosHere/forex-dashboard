resource "google_cloud_run_v2_service" "forex_runner" {
  name     = local.runner_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.common_labels

  template {
    service_account = google_service_account.runtime.email
    timeout         = "3600s"

    scaling {
      min_instance_count = var.runner_min_instances
      max_instance_count = 1
    }

    vpc_access {
      connector = google_vpc_access_connector.forex_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "gcr.io/cloudrun/hello"

      ports {
        container_port = 8080
      }

      # APScheduler needs CPU between HTTP requests to tick — disable CPU throttling.
      resources {
        cpu_idle = false
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
        name = "DISCORD_WEBHOOK_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.human_seeded["discord_webhook_url"].secret_id
            version = "latest"
          }
        }
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

# No google_cloud_run_v2_service_iam_member for allUsers — runner is internal-only.
