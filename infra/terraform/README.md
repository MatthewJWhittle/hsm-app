# Terraform (minimal MVP infra)

This folder contains the long-lived infrastructure baseline.

### Infra vs deployment

| Layer | Owns |
| --- | --- |
| **Terraform (`infra/terraform/`)** | APIs, queues, IAM, budgets, and **stable Cloud Run configuration**: env vars (CORS, GCS, Firebase, **background job queue + OIDC**), scaling bounds, ingress. |
| **GitHub Actions (deploy workflows)** | **Container image rollout only** (`deploy-cloudrun` passes `image`). Revisions keep Terraform-defined env because deploy does not replace the full service spec. |

Do not put job queue URLs or queue IDs in CI secrets for routine deploys—those belong here or in `terraform.tfvars`.

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

### Background jobs (Cloud Tasks) and `JOB_WORKER_URL`

Terraform cannot set `JOB_WORKER_URL` from the same Cloud Run service’s own `.uri` in one apply (circular dependency). Use a **two-step** flow:

1. **First apply** with `api_job_queue_backend_* = "disabled"` (default) and **empty** `api_*_service_public_uri`.
2. Read outputs `api_staging_uri` / `api_prod_uri`, put each value into `api_staging_service_public_uri` / `api_prod_service_public_uri` (HTTPS origin, no trailing slash).
3. Set `api_job_queue_backend_staging` / `api_job_queue_backend_prod` to `cloud_tasks` or `direct` as needed and **apply again**. Plan will fail the `check` blocks until the public URI variables are set when the backend is not `disabled`.

When a public URI is set, Terraform adds `JOB_WORKER_URL` (`{origin}/api/internal/jobs/run`), `CLOUD_TASKS_OIDC_AUDIENCE` (service root), plus `JOB_QUEUE_BACKEND`, `CLOUD_TASKS_*`, and the API runtime service account email for OIDC.

Custom domains: use the HTTPS origin clients use (must match OIDC audience expectations).

## Scope notes

- Keep image tags immutable (Git SHA or digest).
- API image rollout is handled by GitHub Actions deploy workflows.
- `api-staging` and `api-prod` ignore image drift in Terraform via `lifecycle.ignore_changes`.
- Cloud Run env vars are revision-bound; keep full intended env set in Terraform.
- **`api_timeout_seconds`** (Cloud Run, default `60`) is the **platform** ceiling for every request on `api-staging` / `api-prod`. Raise it (e.g. `900`) when background jobs are enabled so it stays **≥** the app’s **`INTERNAL_JOB_HTTP_TIMEOUT_SECONDS`** (worker `POST /api/internal/jobs/run`; default `900` in code). The app also applies a **shorter ASGI timeout** (`HTTP_DEFAULT_REQUEST_TIMEOUT_SECONDS`, default `120`) on all routes **except** that worker path, so normal browser traffic is not held on a 15‑minute window. **`titiler_timeout_seconds`** is separate (default `60`).
- If Firestore already exists, keep `create_firestore_database = false`.

## MVP cost guardrails

- `region = us-central1` baseline
- Cloud Run default scaling:
  - `api_min_instance_count = 0`
  - `api_max_instance_count = 1`
- GCS versioning default disabled
- Optional budget alerts (50%, 90%, 100% thresholds)
