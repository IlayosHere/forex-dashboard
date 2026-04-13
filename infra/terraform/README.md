# forex-dashboard — Terraform (GCP)

This module provisions the full GCP footprint for the forex-dashboard:
Cloud Run (api, ui, runner), Cloud SQL Postgres, VPC Access connector,
Artifact Registry, Secret Manager, IAM, and Workload Identity Federation
for GitHub Actions.

## Bootstrap (one time, manual)

Terraform cannot create its own state bucket (chicken-and-egg) and
needs two APIs enabled before it can enable anything else.

```bash
# 1. Auth locally
gcloud auth login
gcloud auth application-default login
gcloud config set project <PROJECT_ID>

# 2. Create the GCS state bucket (manual, one time)
gsutil mb -l europe-west1 gs://forex-dashboard-tfstate-<PROJECT_ID>
gsutil versioning set on   gs://forex-dashboard-tfstate-<PROJECT_ID>

# 3. Enable the two seed APIs manually
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com
```

## First apply

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — project_id, github_repo, cors_origins

terraform init \
  -backend-config="bucket=forex-dashboard-tfstate-<PROJECT_ID>"
terraform plan
terraform apply
```

The first apply creates all resources with `gcr.io/cloudrun/hello` as
a placeholder image on every Cloud Run service. GitHub Actions rolls
the real images forward on every push to `main`; Terraform does not
fight those rollouts because each service has
`lifecycle.ignore_changes = [template[0].containers[0].image]`.

## Seed human-managed secrets

Terraform creates empty Secret Manager shells for the three secrets
that must not live in state. Populate them once after the first apply:

```bash
# JWT signing key
openssl rand -hex 32 | gcloud secrets versions add jwt_secret --data-file=-

# Auth users (bcrypt JSON — same shape as AUTH_USERS in .env.example)
gcloud secrets versions add auth_users --data-file=auth_users.json

# Discord webhook
printf '%s' "$DISCORD_WEBHOOK_URL" | gcloud secrets versions add discord_webhook_url --data-file=-
```

`database_url` and `db_password` are owned and populated by Terraform —
do not seed them manually.

## Wire GitHub repo secrets

Copy these `terraform output` values into the GitHub repo settings
(Settings → Secrets and variables → Actions):

| Repo secret              | From output                          |
|--------------------------|--------------------------------------|
| `GCP_PROJECT_ID`         | `var.project_id`                     |
| `GCP_REGION`             | `var.region`                         |
| `GCP_WIF_PROVIDER`       | `wif_provider`                       |
| `GCP_DEPLOYER_SA`        | `deployer_sa_email`                  |
| `ARTIFACT_REGISTRY_REPO` | `artifact_registry_repo`             |
| `API_URL`                | `api_url` (also re-read at build time) |
| `UI_URL`                 | `ui_url`                             |

## Notes

- DATABASE_URL is composed in a Terraform local and stored as its own
  Secret Manager secret (`database_url`). Cloud Run env vars cannot
  template a partial secret into a string, so a materialized full URL
  is the cleanest workaround for a VPC-connector + private-IP setup.
- Cloud SQL uses private IP only; Cloud Run reaches it through the
  Serverless VPC Access connector `forex-connector` with
  `egress = PRIVATE_RANGES_ONLY`.
- `deletion_protection = true` on the Cloud SQL instance. To destroy,
  flip to false and apply before `terraform destroy`.
