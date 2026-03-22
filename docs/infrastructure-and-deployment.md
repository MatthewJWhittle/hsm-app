# Infrastructure and deployment

This document describes how to run and deploy the application: target architecture, recommended services, and operational guardrails so infrastructure stays low-ops and low-cost. For the current setup we use **Google Cloud (GCP)** with a stack chosen for solo-developer cost control; the same structure could be adapted for other providers later. It aligns with [Users and use cases](users-and-use-cases.md) (solo app developer) and the cost decisions in [Solution architecture](solution-architecture.md).

---

## Recommended stack (GCP)

| Layer | Service | Why |
|-------|---------|-----|
| **UI** | **Firebase Hosting** | Static React build; free subdomains, SSL, 10 GB hosting. Don’t put the frontend in Cloud Run—it wastes free compute. |
| **API** | **Cloud Run** (FastAPI container) | Managed, scale-to-zero, request-based billing. Free tier: 2M requests/month + CPU/memory allowance. |
| **Tiles** | **Cloud Run** (TiTiler container) | TiTiler as its own Cloud Run service (own container); frontend or backend builds tile URLs pointing at it. Scale-to-zero when not in use. |
| **Database** | **Firestore (Native mode)** | Real free tier: 1 GiB storage, 50k reads/day, 20k writes/day. Avoid Cloud SQL for cost safety—no standing free tier, storage can auto-grow. |
| **Files** | **Cloud Storage** | COGs, uploads, generated files. Free tier in `us-east1`, `us-west1`, `us-central1`: 5 GB-months, limited ops. |
| **Images/builds** | **Artifact Registry** + **Cloud Build** | 0.5 GB free storage; Cloud Build free tier 2,500 build-minutes/month. |
| **Secrets** | **Secret Manager** | Centralised secrets; use instead of env files in production. |

**Cost guardrails:** GCP budgets + alerts, Cloud Run `max-instances` low, `min-instances=0`, request-based billing.

---

## Architecture to deploy

- **Frontend:** React (TypeScript) built in CI → static bundle → **Firebase Hosting**. Calls FastAPI over HTTPS.
- **Backend:** Single FastAPI container on **Cloud Run** — `min-instances=0`, low CPU/memory, `max-instances` set low (e.g. 1–2), sensible request timeout, no always-on background workers.
- **TiTiler:** Own **Cloud Run** service (own container) for raster tiles; frontend builds tile URLs to this service. Scale-to-zero.
- **Database:** **Firestore Native mode** — document-oriented; good for users, catalog metadata, app state, audit. Not ideal for heavy relational joins or complex reporting.
- **Files:** **Cloud Storage** bucket for COGs and uploads; store file metadata and artifact paths in Firestore. Prefer **one object prefix per model** and a **fixed suitability filename** (e.g. `models/{model_id}/suitability_cog.tif`) so uploads scale without encoding display names in blobs — see [Data models — raster naming](data-models.md#raster-files-folders-and-naming-uploads-and-storage).
- **Build/deploy:** Containers in Artifact Registry; build with Cloud Build if convenient.

**Firebase Hosting + Cloud Run together:** Configure Hosting to rewrite a path prefix (e.g. `/api`) to your Cloud Run service URL. Then `/` serves the React app and `/api/*` is proxied to FastAPI on Cloud Run—one origin, no CORS for API calls. Frontend uses relative URLs (e.g. `fetch('/api/models')`). See [Firebase Hosting with Cloud Run](https://firebase.google.com/docs/hosting/cloud-run).

**Auth:** Frontend uses Firebase Auth SDK, gets an ID token, and sends it as `Authorization: Bearer <token>` to the API. FastAPI verifies the token with the Firebase Admin SDK (e.g. `auth.verify_id_token()`). Use this to protect admin routes. See [Verify ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens).

**Use Firebase Hosting (classic), not Firebase App Hosting**—App Hosting is for frameworks like Next.js with SSR; for a React SPA + separate FastAPI API, Hosting in front of Cloud Run is the right fit.

**Caveat:** Firebase does not mean “free forever”; cost safety comes from using the right products and setting limits (budgets, max-instances) as above.

---

## What to avoid (quiet cost drivers on GCP)

- **Cloud SQL / Postgres** — No standing free tier; storage can auto-grow and not shrink. Only add once the app has proven demand and you need relational features.
- **GKE** — Cluster free tier does not cover compute/networking; not a solo-dev low-risk option.
- **Serverless VPC connectors** — Incur charges; use Direct VPC egress if you need VPC later (scale-to-zero, cheaper).
- **Cloud SQL private networking too early** — Adds infrastructure and cost surface.
- **Containerising the frontend for production** — Unnecessary unless you need SSR.
- **Verbose logging everywhere** — 50 GiB log ingestion free; alerting becomes chargeable (e.g. from May 2026); keep monitoring simple.

---

## Cost control in practice (GCP)

1. **One region, keep it simple.** For lowest cost use **`us-central1`** (or `us-east1` / `us-west1`) for Cloud Run, Firestore, and Cloud Storage so you get free-tier coverage on Storage; Tier 1 regions are cheaper for Cloud Run.
2. **Cloud Run limits.** Start with: `min-instances=0`, `max-instances=1` or `2`, small CPU/memory, **request-based billing**. Caps concurrency and runaway scaling.
3. **Billing budget and alerts immediately.** Set a budget and alerts (e.g. 50%, 90%, 100%); optionally wire to automation. See [GCP budgets and notifications](https://cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications).
4. **Optional: automatic kill switch.** Google documents disabling billing when a threshold is hit—stops all billable services. Use as emergency brake only. See [Disable billing with notifications](https://cloud.google.com/billing/docs/how-to/disable-billing-with-notifications).
5. **Firestore indexes.** Avoid over-indexing; use index exemptions for fields you don’t query (e.g. TTL, large arrays/maps). See [Firestore best practices](https://cloud.google.com/firestore/docs/best-practices).

---

## Start with / do not start with (GCP)

**Start with:** Firebase Hosting, Cloud Run, Firestore, Cloud Storage, Secret Manager.

**Do not start with:** Cloud SQL, GKE, VPC connectors, background worker infrastructure, always-on VMs.

---

## Deployment

- **Frontend:** Build React app (e.g. `npm run build`), deploy to Firebase Hosting (`firebase deploy`). Ensure `firebase.json` rewrites `/api` to the FastAPI Cloud Run URL.
- **Backend (FastAPI):** Build Docker image, push to Artifact Registry, deploy to Cloud Run (e.g. `gcloud run deploy`). Set env vars for Firestore, GCS bucket, TiTiler URL. Use Secret Manager for credentials.
- **TiTiler:** Build and deploy TiTiler as a separate Cloud Run service (e.g. image that serves TiTiler with access to GCS bucket or mounted COGs). Frontend or FastAPI constructs tile URLs to this service.
- **Order:** Deploy TiTiler and FastAPI first, then configure Hosting rewrites to point to the FastAPI service URL; then deploy the frontend.
- **Incidents:** Check Cloud Run logs (FastAPI and TiTiler), Firebase Hosting status, and Firestore/Cloud Storage availability. Set up basic health endpoints (`/health`) and optional uptime checks.

## Objectives and monitoring

Define clear product objectives (e.g. “users can find areas of interest faster”, “admins can add a model without developer help”) and instrument the app so you can measure progress: e.g. event logging or analytics for key actions (model selected, point inspected, admin upload), plus simple dashboards or log queries. Use this to validate MVP success and prioritise post-MVP work. Keep monitoring lightweight (e.g. Cloud Monitoring, or a minimal analytics layer) so it doesn’t add cost or complexity early on.

## Expected cost (GCP, light traffic)

With light traffic and staying inside free allowances: **£0 to low single digits per month.** Unpleasant bills usually come from adding relational DBs, VPC plumbing, workers, excessive logs, or uncapped auto-scaling—not from the core app.

---

## References (GCP)

- [Free Google Cloud features and trial](https://cloud.google.com/free/docs/free-cloud-features)
- [Firestore quotas (Native mode)](https://cloud.google.com/firestore/quotas)
- [Firebase Hosting](https://firebase.google.com/docs/hosting)
- [Firebase Hosting with Cloud Run](https://firebase.google.com/docs/hosting/cloud-run)
- [Verify ID Tokens (Firebase Auth)](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [Cloud Run cost optimization](https://cloud.google.com/run/docs/tips/services-cost-optimization)
- [Cloud Run max instances](https://cloud.google.com/run/docs/configuring/max-instances)
- [Budgets and programmatic notifications](https://cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications)
- [Disable billing with notifications](https://cloud.google.com/billing/docs/how-to/disable-billing-with-notifications)
- [Firestore best practices](https://cloud.google.com/firestore/docs/best-practices)
- [VPC egress vs connectors](https://cloud.google.com/run/docs/configuring/connecting-vpc)
