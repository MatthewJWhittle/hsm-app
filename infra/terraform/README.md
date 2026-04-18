# Terraform (minimal MVP infra)

This folder contains the long-lived infrastructure baseline. Terraform owns
service shape and IAM; GitHub Actions owns app image rollout.

## What this creates

- Required project APIs (`run`, `artifactregistry`, `firestore`, `storage`, `secretmanager`)
- Artifact Registry Docker repository
- Cloud Run v2 services (`api-staging`, `api-prod`, `titiler-shared`)
- Service accounts for runtime services
- IAM bindings for runtime access to Firestore, GCS, and Secret Manager
- Optional GCS bucket for model artifacts
- Optional Firestore `(default)` database
- Optional billing budget alerts

## Inputs you must set

Copy `terraform.tfvars.example` to `terraform.tfvars` and set at least:

- `project_id`
- `api_container_image_staging`
- `api_container_image_prod`
- `firebase_web_api_key_secret_name`
- `firebase_project_id`

## Recommended workflow

```bash
cd infra/terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Scope notes

- Keep image tags immutable (Git SHA or digest).
- API image rollout is handled by GitHub Actions deploy workflows.
- `api-staging` and `api-prod` ignore image drift in Terraform via `lifecycle.ignore_changes`.
- Cloud Run env vars are revision-bound; keep full intended env set in Terraform.
- If Firestore already exists, keep `create_firestore_database = false`.
- `api_timeout_seconds` defaults to `120` to reduce timeout risk on rare admin raster replacement
  requests (`POST /api/projects/{project_id}/environmental-cogs`).

## MVP cost guardrails

- `region = us-central1` baseline
- Cloud Run default scaling:
  - `api_min_instance_count = 0`
  - `api_max_instance_count = 1`
- GCS versioning default disabled
- Optional budget alerts (50%, 90%, 100% thresholds)
