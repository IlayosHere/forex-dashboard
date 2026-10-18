# Token the API uses to read (and add queue files to) the private prop-pipeline repo
# for the Research page. A fine-grained GitHub token limited to that one repository.
#
# Terraform seeds a PLACEHOLDER first version so the Cloud Run revision can start before
# the real token exists (a secret reference with no version fails the deploy). Until the
# real token is added the Research page shows a "GitHub answered 401" error; nothing else
# is affected. Add the real token as a NEW version, never through Terraform:
#   gcloud secrets versions add prop_pipeline_github_token --data-file=<(printf '%s' "$TOKEN")
# `version = "latest"` picks it up on the next revision. See docs/research-page.md.
resource "google_secret_manager_secret" "prop_pipeline_github_token" {
  secret_id = "prop_pipeline_github_token"
  labels    = local.common_labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "prop_pipeline_github_token_placeholder" {
  secret      = google_secret_manager_secret.prop_pipeline_github_token.id
  secret_data = "placeholder-replace-me"

  lifecycle {
    ignore_changes = [secret_data]
  }
}
