variable "project_id" {
  description = "GCP project ID that owns all forex-dashboard resources."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run, Cloud SQL, Artifact Registry, and VPC connector."
  type        = string
  default     = "europe-west1"
}

variable "github_repo" {
  description = "GitHub repository in 'owner/repo' form, bound to the Workload Identity Federation provider."
  type        = string
}

variable "cors_origins" {
  description = <<-EOT
    Comma-separated CORS allow-list for the API.
    MUST be set in terraform.tfvars to the exact forex-ui Cloud Run URL
    (and any custom domain) before the first production deploy.
    A wildcard default is intentionally NOT provided: the UI stores JWTs
    in localStorage, so `*` + client-readable tokens is a CSRF/exfil risk.
  EOT
  type        = string
}
