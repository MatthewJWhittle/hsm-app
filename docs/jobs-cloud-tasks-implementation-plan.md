# Jobs + Cloud Tasks implementation plan

This document tracks the rollout of **generic background jobs** (decoupled from environmental COGs only) and **Google Cloud Tasks** for reliable worker invocation on Cloud Run. It aligns with issue **#59** (synchronous replace exceeding ~60s) and scales to other heavy admin routes.

---

## Problem recap

- GCS **upload** (signed URL) succeeds; **`POST /api/projects/{id}/environmental-cogs`** runs **validate → persist → derive → explainability Parquet → catalog** in **one HTTP request**.
- Large COGs exceed **~60s** → **504** / upstream timeout (platform deadline), not a typical 422 from app code.
- **FastAPI `BackgroundTasks`** is **not** sufficient on Cloud Run for long work (CPU/lifecycle, no durable retries).

---

## Principles

1. **Jobs are generic:** `Job` has `kind`, `status`, `input`, errors, timestamps—not a COG-specific subsystem.
2. **Cloud Tasks** schedules a **second HTTP request** to **our** worker; it does not run Python for us.
3. **One executor:** `execute_job(job_id)` in code; enqueue is pluggable (`cloud_tasks` vs `direct` for local/tests). **`direct` blocks** the caller until the worker HTTP handler finishes the job (the enqueue HTTP round-trip is synchronous); **`cloud_tasks` does not** (task queued, worker runs later).
4. **Idempotency** for enqueue and safe worker retries.

---

## Phase 0 — Design (complete)

| Item | Decision |
|------|----------|
| **States** | `queued` → `running` → `succeeded` \| `failed` |
| **First `kind`** | `environmental_cog_replace` |
| **Input** | `{ "project_id", "upload_session_id" }` (validated per kind) |
| **Idempotency** | Optional header/key → Firestore `job_idempotency` doc |
| **Worker auth** | OIDC (Tasks SA → Cloud Run) in prod; dev secret or direct call |

---

## Phase 1 — Firestore + schemas (**complete**)

- [x] `schemas_job.py` — Pydantic models, per-kind input validation.
- [x] `jobs.py` — `jobs` + `job_idempotency` collections; `create_job`, `get_job`, status updates, `try_claim_job` (transactional).
- [x] `tests/test_jobs.py` — schema + persistence behavior (mocked Firestore).

---

## Phase 2 — `JobQueue` interface (**complete**)

- [x] `job_queue.py` — `JobQueue` protocol, `DisabledJobQueue`, `DirectJobQueue`, `CloudTasksJobQueue`, `build_job_queue(settings)`.
- [x] Settings — `JOB_QUEUE_BACKEND`, `CLOUD_TASKS_*`, `JOB_WORKER_URL`, OIDC fields, `INTERNAL_JOB_SECRET`, `JOB_DIRECT_HTTP_TIMEOUT_SECONDS` (each accepts env **or** Python field name via `AliasChoices`).
- [x] Dependency: `google-cloud-tasks`.
- [x] `tests/test_job_queue.py`.

---

## Phase 3 — Worker route (**complete**)

- [x] `POST /api/internal/jobs/run` — body `{"job_id": "..."}`, `include_in_schema=False`.
- [x] `job_worker_auth.verify_internal_job_caller` — `X-Internal-Job-Secret` **or** Bearer OIDC (`CLOUD_TASKS_OIDC_AUDIENCE` / worker URL).
- [x] `job_runner.execute_job` — claim job, run kind-specific work, `complete_job_success` / `complete_job_failure`; avoid re-raising after recording failure (limits Cloud Tasks retry storms).

---

## Phase 4 — Migrate `environmental_cog_replace` (**complete**)

- [x] `env_cog_replace_pipeline.replace_project_environmental_cogs_pipeline` — shared sync implementation.
- [x] `POST .../environmental-cogs` — when `JOB_QUEUE_BACKEND` is **not** `disabled`/`off`/`none` **and** only `upload_session_id` (no multipart), **`create_job` + enqueue + 202** with `Location: /api/jobs/{id}`; otherwise synchronous pipeline. Multipart remains synchronous.
- [x] `GET /api/jobs/{job_id}` (admin Bearer) for status polling.
- [x] Default **`JOB_QUEUE_BACKEND=disabled`** in tests/local keeps today’s synchronous behavior.

---

## Phase 5 — Infrastructure (Terraform / gcloud) (**complete** in repo)

- [x] Enable **`cloudtasks.googleapis.com`** alongside existing project services.
- [x] **`google_cloud_tasks_queue`** — id `var.cloud_tasks_queue_name` (default `hsm-jobs`), location `var.cloud_tasks_queue_location` (default `us-central1`).
- [x] **IAM** — runtime API SAs (`api_staging`, `api_prod`) → `roles/cloudtasks.enqueuer`; same SAs → `roles/run.invoker` on their Cloud Run service (OIDC self-call for the worker URL).
- [ ] **Deploy-time env** (outside Terraform / CI): set `JOB_QUEUE_BACKEND=cloud_tasks`, **`CLOUD_TASKS_QUEUE_ID`** (match Terraform queue name, default `hsm-jobs`), `CLOUD_TASKS_LOCATION`, **`JOB_WORKER_URL`** (full `POST` URL to `/api/internal/jobs/run`), **`CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL`**. Prefer **OIDC-only** worker auth: **omit `INTERNAL_JOB_SECRET`** in production — if set, the worker accepts the secret and **does not** verify OIDC for that request. Raise **Cloud Run request timeout** if the worker must run longer than the default for large COGs.

---

## Phase 6 — Admin UI (**complete**)

- [x] `replaceProjectEnvironmentalCog` handles **202** — poll `GET /api/jobs/{job_id}` with exponential backoff (cap 10s, overall deadline 45m), then **`GET /api/projects/{id}`** to refresh the catalog row.
- [x] Upload status strings while the job is **queued** / **running**.

---

## Phase 7 — Observability (**partial** / ongoing)

- [x] Worker logs: `execute_job start` / `succeeded` with **`duration_ms`**; HTTP and unexpected failures include **`duration_ms`** in log context.
- [ ] Dashboard alerts on failure rate / retry storms (ops follow-up).

---

## Phase 8 — Rollout (checklist)

1. [x] Ship job storage, worker, Terraform queue/IAM scaffolding, and admin UI polling; **`JOB_QUEUE_BACKEND`** defaults keep **synchronous** behavior until explicitly configured.
2. [ ] **Apply Terraform** (or equivalent) so `cloudtasks.googleapis.com`, the **jobs queue**, and **IAM** (`cloudtasks.enqueuer`, self **`run.invoker`**) match the target project.
3. [ ] **Configure Cloud Run** (staging): `JOB_QUEUE_BACKEND=cloud_tasks`, `CLOUD_TASKS_QUEUE_ID` (e.g. `hsm-jobs`), `CLOUD_TASKS_LOCATION`, full **`JOB_WORKER_URL`**, **`CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL`**, **`CLOUD_TASKS_OIDC_AUDIENCE`** if it differs from the worker URL, **no `INTERNAL_JOB_SECRET`** unless you intentionally use secret auth, and a **request timeout** suited to large COGs.
4. [ ] **Soak** staging with a large environmental COG (upload-session path returns **202**; confirm job + catalog update end-to-end).
5. [ ] **Production** after staging sign-off; multipart replace remains synchronous by design.

---

## Cost notes

- **Cloud Tasks:** usually low at admin volumes.
- **Firestore:** extra writes/reads per job + polling (mitigate with backoff).
- **Cloud Run:** compute similar to today; watch **retries** and **long worker timeouts**.

---

## References

- [`docs/issue-59-investigation-guide.md`](issue-59-investigation-guide.md)
- Backend: `backend_api/routers/projects.py` (route), `backend_api/env_cog_replace_pipeline.py` (pipeline + worker)
