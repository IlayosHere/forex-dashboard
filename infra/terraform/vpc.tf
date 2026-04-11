data "google_compute_network" "default" {
  name = "default"

  depends_on = [google_project_service.enabled]
}

# Reserved /24 inside the default VPC for Google-managed services (Cloud SQL private IP).
resource "google_compute_global_address" "private_services" {
  name          = "forex-private-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = data.google_compute_network.default.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = data.google_compute_network.default.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}

# Serverless VPC Access connector — Cloud Run → Cloud SQL private IP.
resource "google_vpc_access_connector" "forex_connector" {
  name          = "forex-connector"
  region        = var.region
  network       = data.google_compute_network.default.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 3

  depends_on = [google_project_service.enabled]
}
