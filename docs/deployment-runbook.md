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

For PR validation, use a Firebase Hosting preview channel for frontend changes while pointing at shared staging backend.

**Firebase Hosting (two sites, one project):**

- **Prod** site id `hsm-dashboard` — live channel rewrites `/api` → Cloud Run **`api-prod`**. The static bundle is deployed when you **publish a GitHub Release** (same tagged commit as `api-prod`), in **`deploy-prod.yml`** after the Cloud Run deploy step in the same job.
- **Dev** site id `hsm-dashboard-dev` — live channel rewrites `/api` → Cloud Run **`api-staging`**. Deployed on **merge to `main`** after CI (`firebase-hosting-merge.yml`). Shared Auth/Firestore with prod. Expected URLs: `https://hsm-dashboard-dev.web.app` (and `.firebaseapp.com`).

Create `hsm-dashboard-dev` once (`firebase hosting:sites:create` or Firebase console → Hosting → Add site), then map deploy targets in `.firebaserc` (`firebase target:apply`). See [issue #44](https://github.com/MatthewJWhittle/hsm-app/issues/44).

## 2) Core rules

- **Build once, promote forward:** build one image per commit and deploy by immutable tag or digest.
- **Clear ownership split:** Terraform manages long-lived infra shape; GitHub Actions manages app rollout.
- **Separate service config:** keep staging and prod as separate services to keep config boundaries clear.
- **Revision-safe deploys:** Cloud Run env vars are revision-bound, so each deploy sets the complete intended env set.
- **Low-ops rollouts:** use Cloud Run built-in revision tags, traffic migration, and rollback.
- **Cost control by default:** `min-instances=0`, low `max-instances`, request-based billing, budgets + alerts.

## 3) Initial bootstrap (manual, one time)

1. Create Artifact Registry repository for backend images.
2. Deploy a known-good image to `api-staging`.
3. Validate smoke checks on staging.
4. Deploy the same image to `api-prod`.
5. Configure Firebase Hosting: **prod** site live channel rewrites `/api` to `api-prod`; add **dev** site and map Hosting rewrites for `/api` to `api-staging` (see §1).
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
2. GitHub Actions workflow `backend-deploy-staging.yml` builds and pushes backend image.
3. GitHub Actions deploys image to `api-staging`.
4. GitHub Actions deploys the **dev** Hosting site (`hsm-dashboard-dev`) from the same `main` commit.

GitHub Actions settings for preview builds:

- Secret: `VITE_FIREBASE_API_KEY`
- Variable: `PREVIEW_API_BASE_URL`

CLI examples:

```bash
gh secret set VITE_FIREBASE_API_KEY --body "<firebase-web-api-key>"
gh variable set PREVIEW_API_BASE_URL --body "https://api-staging-<project-number>.us-central1.run.app/api"
```

Important:

- Set `PREVIEW_API_BASE_URL` to the API origin **including** `/api`.
- Canonical API paths are `/api/*` in both Hosting and direct Cloud Run usage (for example `/api/health`, `/api/models`).
- Configure backend CORS for previews with `CORS_ORIGIN_REGEX` (for example `^https://hsm-dashboard--pr[0-9]+-[a-z0-9-]+\\.web\\.app$`) so new PR channels do not require manual allowlist updates.

Backend deploys are handled by GitHub Actions deploy workflows.

Notes:

- This keeps environments simple while avoiding backend deploy churn on every PR update.
- If PR concurrency becomes too high, revisit whether additional staging services are needed.

### CD — deploy workflows (GitHub Actions)

Use GitHub Actions for staging rollouts and prod releases:

- Workflow A (`backend-deploy-staging.yml`): on `main` CI success, build/push backend image and deploy `api-staging`
- Workflow B (`firebase-hosting-merge.yml`): on `main` CI success, build frontend and deploy **dev** Hosting (`hsm-dashboard-dev`)
- Workflow C (`deploy-prod.yml`): on GitHub release publication, one job on the tagged commit — deploy **`api-prod`**, then **prod** Hosting (`hsm-dashboard`) in sequence

Authentication uses GitHub OIDC + Workload Identity Federation (`google-github-actions/auth`).

Required GitHub Actions repository variables for backend deploy workflows:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `ARTIFACT_REPOSITORY`
- `BACKEND_IMAGE_NAME`
- `BACKEND_STAGING_SERVICE_NAME`
- `BACKEND_PROD_SERVICE_NAME`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`

Required repository secrets:

- `VITE_FIREBASE_API_KEY` (frontend build)
- `FIREBASE_SERVICE_ACCOUNT_HSM_DASHBOARD` (Firebase Hosting deploy)

## 5) Production release flow (CD)

1. Merge to `main` to produce and validate a staging deployment.
2. Run smoke/integration checks on staging.
3. Create/publish a GitHub release tag for the validated commit.
4. GitHub Actions runs **`deploy-prod.yml`** once: deploy **`api-prod`**, then **prod Hosting** (`hsm-dashboard`) in the same job (same tag).
5. If needed, roll back by redeploying a prior known-good digest.

Promotion path:

`build (main) -> staging API + dev Hosting -> verify -> release tag -> prod API + prod Hosting`

## 6) Configuration and secret management

- Keep staging and prod secrets separate.
- Store sensitive values in Secret Manager; inject at deploy.
- Set full env var sets per revision deploy (do not rely on partial mutation).
- Keep runtime endpoints explicit, including the shared TiTiler URL.

## 7) Scope boundaries

Do:

- Keep the architecture minimal for MVP.
- Use immutable image tags/digests for traceability.
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

