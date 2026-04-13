# Terraform (minimal MVP infra)

This folder contains a minimal Terraform baseline for review-first infrastructure setup.

It matches the deployment plan in `docs/deployment-runbook.md`:

- Cloud Run API split: `api-staging` and `api-prod`
- Shared, stable TiTiler URL (not managed here)
- Artifact Registry for backend images
- Optional model-artifact GCS bucket
- Optional Firestore Native database creation
- Optional monthly budget alerts (Cloud Billing budget resource)

## What this creates

- Required project APIs (`run`, `artifactregistry`, `firestore`, `storage`, `secretmanager`, `cloudbuild`)
- Artifact Registry Docker repository
- Service accounts for API runtime (`hsm-api-staging`, `hsm-api-prod`)
- Cloud Run v2 services (`api-staging`, `api-prod`)
- IAM bindings:
  - Firestore user role for both runtime service accounts
  - Storage object admin on model bucket (if bucket managed here)
  - Secret Manager accessor for Firebase Web API key secret
  - Optional unauthenticated Cloud Run invoker (`allUsers`)
- Optional GCS bucket for model artifacts
- Optional Firestore `(default)` database

## Inputs you must set

Copy `terraform.tfvars.example` to `terraform.tfvars` and set at least:

- `project_id`
- `api_container_image_staging`
- `api_container_image_prod`
- `titiler_url`
- `firebase_web_api_key_secret_name`

## Review-only workflow

No deployment has been run by this change.

Recommended review commands:

```bash
cd infra/terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars
```

## Notes

- Keep image tags immutable (Git SHA).
- Cloud Run env vars are revision-bound; keep full intended env set in Terraform.
- If Firestore already exists, keep `create_firestore_database = false`.
- For stricter production access, set `allow_unauthenticated_api = false` and front the API via Hosting/API Gateway as needed.

## MVP cost guardrails implemented

- `region = us-central1` (free-tier-friendly baseline)
- Cloud Run scaling defaults:
  - `api_min_instance_count = 0`
  - `api_max_instance_count = 1`
- GCS bucket versioning default disabled (`gcs_enable_versioning = false`) to avoid version-storage growth.
- Optional budget alerts:
  - `create_budget_alerts = true`
  - `monthly_budget_amount_usd = 5`
  - thresholds at `50%`, `90%`, and `100%`

If you do not yet have a billing account id or notification channels, keep budget alerts disabled until ready.
