# Deployment runbook (MVP)

This runbook turns the deployment direction in [Infrastructure and deployment](infrastructure-and-deployment.md) into an execution plan for initial launch and ongoing CI/CD.

It is aligned with issue [#27](https://github.com/MatthewJWhittle/hsm-app/issues/27) and assumes:

- FastAPI is deployed on Cloud Run.
- TiTiler is stable and shared (no separate staging/prod split for now).
- Frontend is deployed to Firebase Hosting.

## 1) Target deployment pattern

Use two Cloud Run services for the API:

- `api-staging`
- `api-prod`

Do not create one Cloud Run service per PR by default.

For PR validation, deploy a new revision on `api-staging` with `0%` traffic and a revision tag (for example `pr-123`), then test via the tag URL.

## 2) Core rules

- **Build once, promote forward:** build one image per commit and tag immutably (recommended format: `<git-sha-12>-<arch>`, for example `abc123def456-amd64`).
- **Clear ownership split:** Terraform manages Cloud Run service shape; CI/CD manages API revision rollout.
- **Separate service config:** keep staging and prod as separate services to keep config boundaries clear.
- **Revision-safe deploys:** Cloud Run env vars are revision-bound, so each deploy sets the complete intended env set.
- **Low-ops rollouts:** use Cloud Run built-in revision tags, traffic migration, and rollback.
- **Cost control by default:** `min-instances=0`, low `max-instances`, request-based billing, budgets + alerts.

## 3) Initial bootstrap (manual, one time)

1. Create Artifact Registry repository for backend images.
2. Deploy a known-good image to `api-staging`.
3. Validate smoke checks on staging.
4. Deploy the same image to `api-prod`.
5. Configure Firebase Hosting live channel to rewrite `/api` to `api-prod`.
6. Confirm runtime limits and billing guardrails:
  - `min-instances=0`
  - `max-instances=1` or `2` initially
  - request-based billing
  - billing budget alerts

## 4) PR / development validation flow (CI)

On pull request:

1. Run tests/lint/build.
2. Deploy frontend to a Firebase Hosting preview channel.
3. Point preview frontend to `PREVIEW_API_BASE_URL` (staging API origin).

Backend staging deployment happens from `main` pushes (not from PR events):

1. Merge to `main`.
2. Cloud Build trigger `backend-staging-main` builds and pushes backend image.
3. Cloud Build deploys image to `api-staging`.

GitHub Actions settings for preview builds:

- Secret: `VITE_FIREBASE_API_KEY`
- Variable: `PREVIEW_API_BASE_URL`

CLI examples:

```bash
gh secret set VITE_FIREBASE_API_KEY --body "<firebase-web-api-key>"
gh variable set PREVIEW_API_BASE_URL --body "https://api-staging-<project-number>.us-central1.run.app"
```

Important:

- Set `PREVIEW_API_BASE_URL` to the API origin **without** `/api`.
- `/api` is a Firebase Hosting rewrite concern; direct Cloud Run calls use root paths like `/health`, `/models`, etc.
- Configure backend CORS for previews with `CORS_ORIGIN_REGEX` (for example `^https://hsm-dashboard--pr[0-9]+-[a-z0-9-]+\\.web\\.app$`) so new PR channels do not require manual allowlist updates.

Backend deploys are handled by Cloud Build triggers, not GitHub Actions deploy jobs.

Notes:

- This keeps environments simple while avoiding backend deploy churn on every PR update.
- If PR concurrency becomes too high, revisit whether additional staging services are needed.

### Backend CD (Cloud Build)

Use Cloud Build triggers for backend release automation:

- Trigger A (automatic): push to `main` -> build/push backend image -> deploy `api-staging`
- Trigger B (release): push a release tag (for example `v1.0.0`) -> build/push backend image -> deploy `api-prod`

Config files in repo:

- `cloudbuild.backend.staging.yaml`
- `cloudbuild.backend.prod.yaml`

Cloud Build triggers are created by Terraform (`create_cloud_build_triggers = true`).

Prerequisite for first setup:

1. Create and authorize the Cloud Build GitHub host connection in Cloud Console (2nd gen).
2. Link the repository.
3. Set `cloud_build_github_app_installation_id` in `terraform.tfvars` so Terraform can manage the same connection resource.

Release flow example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Required IAM for Cloud Build deploy identity:

- `roles/artifactregistry.writer`
- `roles/run.admin`
- `roles/iam.serviceAccountUser` on runtime service accounts used by Cloud Run

These IAM bindings are managed in Terraform.

## 5) Production release flow (CD)

1. Merge to `main` to produce and validate a staging deployment.
2. Run smoke/integration checks on staging.
3. Create and push release tag (for example `v1.0.0`).
4. Cloud Build trigger `backend-prod-release` builds/pushes image and deploys `api-prod`.
5. If needed, roll back by redeploying a prior known-good release tag/image.

Promotion path:

`build -> stage -> verify -> prod`

Release command pattern:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 6) Configuration and secret management

- Keep staging and prod secrets separate.
- Store sensitive values in Secret Manager; inject at deploy.
- Set full env var sets per revision deploy (do not rely on partial mutation).
- Keep runtime endpoints explicit, including the shared TiTiler URL.

## 7) Scope boundaries

Do:

- Keep the architecture minimal for MVP.
- Use revision tags for traceability and testing.
- Track PR number, revision tag, and SHA in CI logs.

Do not:

- Emulate Azure deployment slots.
- Create permanent per-branch environments.
- Rely on one untagged staging revision for all PR testing.

## 8) Follow-on work

Priority issues linked to this runbook:

- [#27](https://github.com/MatthewJWhittle/hsm-app/issues/27): deploy and backend preview capability
- [#36](https://github.com/MatthewJWhittle/hsm-app/issues/36): scripted admin auth path for automation
- [#32](https://github.com/MatthewJWhittle/hsm-app/issues/32): first-use interpretation guardrail before pilot
- [#18](https://github.com/MatthewJWhittle/hsm-app/issues/18) and [#23](https://github.com/MatthewJWhittle/hsm-app/issues/23): CI/docs alignment hardening

