resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "forex_db" {
  name             = "forex-db"
  database_version = "POSTGRES_16"
  region           = var.region

  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
      start_time                     = "02:00"
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    user_labels = local.common_labels
  }

  depends_on = [
    google_project_service.enabled,
  ]
}

resource "google_sql_database" "forex" {
  name     = "forex"
  instance = google_sql_database_instance.forex_db.name
}

resource "google_sql_user" "forex" {
  name     = "forex"
  instance = google_sql_database_instance.forex_db.name
  password = random_password.db.result
}
