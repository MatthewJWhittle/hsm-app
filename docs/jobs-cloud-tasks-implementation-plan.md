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
3. **One executor:** `execute_job(job_id)` in code; enqueue is pluggable (`cloud_tasks` vs `direct` for local/tests).
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

## Phase 3 — Worker route

- `POST /internal/jobs/run` (or under `/api/internal/...`, hidden from OpenAPI).
- Verify OIDC / secret → `execute_job(job_id)` → 2xx/5xx for Tasks retries.

---

## Phase 4 — Migrate `environmental_cog_replace`

- Extract pipeline from `replace_project_environmental_cogs` into a handler module.
- Public route returns **202** + `job_id`; worker runs the same logic.

---

## Phase 5 — Infrastructure (Terraform / gcloud)

- Cloud Tasks queue(s); Tasks SA + `run.invoker`; API SA + task creator role.
- Cloud Run timeout/env for worker path.

---

## Phase 6 — Admin UI

- Poll `GET /api/jobs/{id}` with backoff; surface errors.

---

## Phase 7 — Observability

- Structured logs: `job_id`, `kind`, phase durations; alert on failure rate / retry storms.

---

## Phase 8 — Rollout

1. Ship job storage + worker behind flag.
2. Staging: **202** for environmental COG replace; soak with large COG.
3. Prod; remove sync fallback when stable.

---

## Cost notes

- **Cloud Tasks:** usually low at admin volumes.
- **Firestore:** extra writes/reads per job + polling (mitigate with backoff).
- **Cloud Run:** compute similar to today; watch **retries** and **long worker timeouts**.

---

## References

- [`docs/issue-59-investigation-guide.md`](issue-59-investigation-guide.md)
- Backend: `backend_api/routers/projects.py` (`replace_project_environmental_cogs`)
