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

- **Build once, promote forward:** build one image per commit and tag with Git SHA.
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
2. Build backend image and push with SHA tag.
3. Deploy image to `api-staging` as a new revision with `0%` traffic.
4. Tag the revision as `pr-<number>`.
5. Publish API test URL from the tagged revision.
6. Deploy frontend to a Firebase Hosting preview channel.
7. Point preview frontend to the tagged staging API URL.

Notes:

- This keeps environments simple while still allowing isolated API verification per PR.
- If PR concurrency becomes too high, revisit whether additional staging services are needed.

## 5) Production release flow (CD)

On merge to `main`:

1. Deploy candidate revision to `api-staging`.
2. Run smoke/integration checks.
3. Deploy the same SHA image to `api-prod` at `0%` traffic.
4. Shift traffic gradually (for example `10% -> 50% -> 100%`).
5. If needed, roll back by shifting traffic to a previous healthy revision.

Promotion path:

`build -> stage -> verify -> prod`

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
