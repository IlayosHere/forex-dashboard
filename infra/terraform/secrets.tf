locals {
  # Human-seeded secrets: Terraform creates the empty shell; values are added
  # post-apply via `gcloud secrets versions add`.
  human_seeded_secrets = toset([
    "jwt_secret",
    "auth_users",
    "discord_webhook_url",
  ])
}

resource "google_secret_manager_secret" "human_seeded" {
  for_each = local.human_seeded_secrets

  secret_id = each.value
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

# DB password — Terraform owns the value (generated) and seeds the first version.
resource "google_secret_manager_secret" "db_password" {
  secret_id = "db_password"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db.result
}

# DATABASE_URL — composed in a local (private_ip + password) and stored as a
# single secret so Cloud Run can mount it via value_source.secret_key_ref.
# Cloud Run env vars cannot template secret values inside a string, which is
# why we materialize the full URL here instead of assembling it at runtime.
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database_url"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}
