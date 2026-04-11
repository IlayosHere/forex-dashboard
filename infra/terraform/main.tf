terraform {
  backend "gcs" {
    # Bucket name must be provided at init time via:
    #   terraform init -backend-config="bucket=forex-dashboard-tfstate-<project_id>"
    # The bucket itself is bootstrapped out-of-band (see README.md).
    prefix = "forex-dashboard"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  # Common labels applied to every managed resource.
  common_labels = {
    app        = "forex-dashboard"
    managed_by = "terraform"
  }

  # Cloud Run service names.
  api_service_name    = "forex-api"
  ui_service_name     = "forex-ui"
  runner_service_name = "forex-runner"

  # Fully-composed DATABASE_URL. Stored as its own Secret Manager secret because
  # Cloud Run env `value_source.secret_key_ref` only supports whole-value secret
  # references — it cannot interpolate a partial secret (the password) into a
  # template string. So we compose the full URL in Terraform and seed it as
  # secret `database_url`, then mount it as a single env var.
  database_url = "postgresql://forex:${random_password.db.result}@${google_sql_database_instance.forex_db.private_ip_address}:5432/forex"
}
