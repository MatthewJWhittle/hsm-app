# Specification: Background worker (Cloud Tasks + Cloud Run)

This document is the canonical spec for moving **infrequent, CPU/memory/time-heavy** work off the **main API** onto **dedicated worker Cloud Run services**, with **Cloud Tasks** as the **durable** queue in **staging and production** (local dev may bypass Tasks; see §10). It supersedes informal design notes and incorporates **security and abuse** requirements from red-team review.

**Related:** [Infrastructure and deployment](infrastructure-and-deployment.md), [Deployment runbook](deployment-runbook.md), root [application-spec.md](../application-spec.md).

---

## 1. Purpose

- Keep the **public API** Cloud Run service **light**: low CPU/memory, **short request timeout**, responsive handlers.
- Run **background** jobs on **environment-specific worker** Cloud Run services (**staging** vs **prod**) with **higher** CPU/memory and **longer** request timeout than the **API** in that environment. **Staging** may use a **lighter** worker profile than **prod** (cost and parity with lower staging SLA).
- The API **does not wait** for job completion: it **creates a job record**, **enqueues** work, returns **202** + `job_id`.
- The worker **writes artifacts** to **GCS** and updates **job state** in **Firestore**.

---

## 2. Goals and non-goals

### Goals

- **202 + `job_id`** for background-eligible operations; no synchronous wait on the worker in the API.
- **Durable** dispatch via **Cloud Tasks** in **staging and prod**: **Cloud Tasks** → HTTPS → **private** worker with **OIDC** (not optional for those environments).
- **One container image**, **four Cloud Run deploy targets** in GCP: **`api-staging`**, **`api-prod`**, **`worker-staging`**, **`worker-prod`** (names align with existing API naming; exact IDs follow Terraform/vars). Same image; **worker** services use a **worker** entrypoint (command/args).
- **Strict environment separation:** the **staging** API enqueues only to the **staging** queue and **staging** worker URL; **prod** API only to **prod** queue and **prod** worker URL. **No** shared worker across envs.
- **Staging worker** may use **lower** `cpu`, `memory`, `timeout`, and **`max_instances`** than **prod** worker; queue **rate limits** may also be looser or tighter per env as needed.
- **Backend layout:** **three Python packages** — **shared library**, **API app**, **worker app** — under `backend/` with **one** lockfile and **one** container image (see §4.4). *(Today’s monolithic `backend_api` may be split incrementally.)*
- **Regional** co-location: each env’s **queue** and **worker** (and API) in the same region (e.g. **`us-central1`**).

### Non-goals (MVP)

- Generic workflow engine or arbitrary user code.
- Separate job database (Firestore job documents are sufficient).
- **Cloud Run Jobs** unless a **single HTTP task** cannot finish within **Cloud Tasks HTTP limits** (see §8).
- An **internal queue / job platform**: no custom lease tables, visibility timeouts, or worker pools—**Cloud Tasks** provides **durable delivery, retries, and rate limits** (see §2.1).

---

## 2.1 What we build vs what Cloud Tasks provides

**We are not building a queue system.** **Cloud Tasks** is the queue: it stores tasks, dispatches HTTPS to the worker, retries on failure, and applies per-queue rate limits.

**We intentionally keep “job management” thin:**

| Layer | Responsibility |
|-------|----------------|
| **Cloud Tasks** | Durability, retry/backoff, dispatch rate, OIDC to private Run. |
| **API** | Authz, create **one Firestore job doc**, `createTask`, return **202** + `job_id`; optional **GET** for status. |
| **Worker** | Claim job by `job_id`, read **`kind` from the Firestore job doc**, run the matching handler, write GCS, update the same job doc. (HTTP body `kind` is optional metadata; log if it disagrees with the doc.) |
| **Firestore** | **State** for UX and idempotency (`pending` / `running` / terminal), not a replacement for Tasks. |

**Defer until there is a concrete need:** admin queue UIs, job priority classes, cancellation APIs, multi-step workflows, fan-out orchestration, or per-tenant queue isolation. Use **Cloud Console** (Tasks + Run logs) and **log-based metrics** first.

**Add new background features** by introducing a **`kind`**, a **handler**, and documented fields on the job doc—**not** by growing a generic job engine.

---

## 3. Architecture

```
Browser → Firebase Hosting (/api) → API (per env: api-staging | api-prod, light limits)
                    │
                    │  create Firestore job (pending)
                    │  Cloud Tasks.create_task (OIDC → worker URL for THAT env)
                    ▼
              Worker (per env: worker-staging | worker-prod)
              staging: lighter CPU/memory/timeout (typical)
              prod:    heavier limits as required
                    │
                    ├─ load canonical inputs from Firestore / GCS (by job_id / refs)
                    ├─ write outputs → GCS
                    └─ update Firestore job → running | succeeded | failed (+ artifacts, safe errors)
```

- **Firebase Hosting** rewrites **`/api/**` only to the API service**. The **worker base URL is not** exposed through Hosting.
- In **staging and production**, the API **must not** invoke the worker synchronously for these flows; **Cloud Tasks** is the only supported dispatch path.

---

## 4. Components

### 4.1 API service

- **Authenticate** requests (Firebase ID token) per existing patterns.
- **Authorize** the operation (admin, project ownership, etc.) **before** creating a job.
- **Create** `jobs/{job_id}` with `status=pending` and **snapshotted** fields the worker needs (kind, `project_id`, `model_id`, allowed output prefixes, etc.). **Do not** rely on the HTTP task body as the source of truth.
- **Schedule** worker execution via the **job dispatcher** (§10.2): in **staging/prod**, a Cloud Tasks HTTP task (POST to **this environment’s** worker URL, OIDC, small JSON; see §5); in **local**, a non-durable **BackgroundTasks** + HTTP POST with the **same body**. Configuration (queue id, worker URL, OIDC SA) is **env-specific** so tasks never target the wrong worker.
- Return **202 Accepted** with **`job_id`** (and optional non-sensitive echo).
- Expose **`GET /api/.../jobs/{job_id}`** (exact path TBD) for **status reads** — thin, no heavy work.

### 4.2 Worker service

- **HTTP handler(s)** invoked by Cloud Tasks (and, in dev only, by local HTTP; see §10).
- **Trust model:** OIDC proves **“Cloud Tasks invoked this service as the configured SA”**. It does **not** prove end-user intent. The worker **must** re-authorize using **Firestore** (§6, §11).
- **Input:** Prefer **minimal** body: at least **`job_id`** and **`kind`**; worker loads **canonical** parameters from the job document.
- **Output:** **2xx** only after outputs are **committed** (objects visible, job doc updated). Otherwise **5xx** for retryable failures (subject to retry caps).
- **Idempotency:** Safe under **duplicate delivery** and **retries** (§6, §11).

### 4.3 Cloud Tasks

- **Queue** per environment (e.g. `background-staging`, `background-prod`).
- **Task:** HTTP **POST**, **OIDC** token; payload per §4.2.
- **Queue configuration:** [retry](https://cloud.google.com/tasks/docs/configuring-queues#retry) and [rate limits](https://cloud.google.com/tasks/docs/configuring-queues#rate) to protect worker, GCS, and Firestore.

### 4.4 Backend code layout (Python)

**Goal:** Separate **API**, **worker**, and **shared** code so boundaries are obvious, without multiple repos or multiple Dockerfiles.

**Import rule:** The **shared** package **must not** import the API or worker. **API** and **worker** import **shared** only. Enforce with structure and review (Python does not enforce this at runtime).

**Packaging — preferred (`uv` native):** A **[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)** under `backend/`: a workspace **root** plus **members** (e.g. `packages/hsm_core`, `packages/hsm_api`, `packages/hsm_worker` — **exact names TBD**), each with its own `pyproject.toml`, and **one `uv.lock`** at the workspace root. Dependencies between members use `workspace = true` in `[tool.uv.sources]`. This matches Astral’s documented pattern (FastAPI application + libraries in one repository).

**Packaging — alternative:** A **single** `pyproject.toml` with **multiple** import packages (e.g. Hatch `[tool.hatch.build.targets.wheel] packages = [...]`) and one lockfile — fewer files; slightly less aligned with uv’s first-class workspace workflow.

| Package (example name) | Contents |
|------------------------|----------|
| **`hsm_core`** (shared) | Domain logic: storage, raster/Parquet/ingest **services**, shared schemas/types, job payload models. **No** public API routers. |
| **`hsm_api`** | FastAPI **public** app: `main`, lifespan, routers, deps, **job dispatcher** implementation (§10.2). |
| **`hsm_worker`** | Small FastAPI app: HTTP handler(s) for Cloud Tasks; calls into **`hsm_core`**. |

**Docker / Cloud Run:** **One image** from `backend/`; `uv sync` installs all members needed at runtime. Per service, override **[container `command` / `args`](https://cloud.google.com/run/docs/configuring/services/containers)** — e.g. `uvicorn hsm_api.main:app` vs `uvicorn hsm_worker.main:app` (exact module paths follow chosen package names).

**When API and worker share the same heavy deps** (rasterio, ML today), **one** resolved dependency tree is appropriate. If the API later must **omit** large stacks, consider **`[project.optional-dependencies]`** (extras) for a slimmer API install, or **split images** — uv notes **workspaces are a poor fit** when members have **fundamentally conflicting** requirements; then **path dependencies** or separate resolution may be needed ([When (not) to use workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)).

**Local dev:** Same Compose **bind mount** over `backend/` and `uv sync`; **two** services differ only by **command** (API vs worker) and port.

**Migration:** Evolve from the current single **`backend_api`** tree in **incremental** PRs (introduce shared package, add worker app, narrow API) — exact steps are implementation, not blocking this spec.

---

## 5. Security and IAM

| Requirement | Detail |
|-------------|--------|
| Worker ingress | **No** `allUsers` **run.invoker**. Only the **Tasks OIDC service account** (and explicitly approved principals, if any) receive **roles/run.invoker** on the **worker** service. |
| OIDC | Use an **ID token** for Cloud Run targets. Set **audience** to the worker service URL (or a configured [custom audience](https://cloud.google.com/run/docs/configuring/custom-audiences)). |
| Enqueuer | API runtime SA (or dedicated SA) can **create tasks** (e.g. **roles/cloudtasks.enqueuer** on the queue). **Least privilege**; avoid reusing a broad “super” SA across unrelated workloads. |
| Token minting | Cloud Tasks **service agent** has **roles/iam.serviceAccountUser** on the **OIDC SA** per [HTTP target authentication](https://cloud.google.com/tasks/docs/creating-http-target-tasks). |
| OIDC SA project | The SA used for OIDC must be in the **same project** as the Cloud Tasks queue (documented constraint). |
| Task payload | **Identifiers and kind only** where possible. **Secrets, signed URLs, and full path overrides** from untrusted sources must not be required in the body; worker reads **snapshotted** fields from Firestore. |

---

## 6. Job data model (Firestore)

Example fields (names may align with existing collections):

- **`job_id`:** document id — **unguessable** (e.g. UUIDv4 / 128+ bits random). **Never** sequential or short.
- **`status`:** `pending` | `running` | `succeeded` | `failed`
- **`kind`:** enum string per job type
- **`created_at`**, **`updated_at`**
- **`created_by`** (Firebase uid), **`project_id`**, **`model_id`** as needed for **authorization**
- **`error`:** **sanitized** user-safe message/code on failure (no stack traces, no raw GCS/provider errors)
- **`artifacts`:** map of logical names → `gs://…` paths on success

### Firestore rules

- **Client reads/writes** to `jobs/*` are **denied** in `firestore.rules`; only **Admin SDK** on API/worker may access (rules do not apply to the Admin SDK). Other collections may still use a temporary open policy until tightened.

### State transitions

- API creates **`pending`** then enqueues.
- Worker claims work in a **transaction**: **`pending` → `running`**, or reclaims **`running`** with a **fresh `updated_at`** when the lease is **stale** (e.g. process died after claim and Cloud Tasks retries). Staleness is **`WORKER_HTTP_DEADLINE_SECONDS`** (aligned with the worker Cloud Run timeout and Cloud Tasks `dispatch_deadline`) plus optional **`WORKER_STALE_RUNNING_GRACE_SECONDS`** (default **0** so the first retry after a timeout can reclaim; keep grace small). While **`running`** with a **fresh** lease, duplicate deliveries **exit 2xx** without redoing work; terminal **`succeeded` / `failed`** ditto.
- Worker sets **`succeeded`** or **`failed`** once, with consistent artifact pointers.
- **Stale `pending`:** admin **GET** job poll may mark jobs stuck in **`pending`** longer than **`JOB_PENDING_ABANDON_AFTER_SECONDS`** (default 24h) as **`failed`** with **`NEVER_DISPATCHED`** (transactional), e.g. if enqueue never succeeded and no worker ran.

---

## 7. API contract (clients)

- **Enqueue:** **202 Accepted** + JSON body including **`job_id`**.
- **Poll:** **`GET .../jobs/{job_id}`** — **must authorize** every read: same checks as “user may see this project/job” (admin / ownership). Prefer **403** or generic **404** for unauthorized access to avoid **enumeration** leaks (implementation choice documented per route).
- **Errors returned to browsers:** **sanitized**; internal details only in **server logs** (with **redaction** — no `Authorization` headers, no signed URLs in logs).

Interactive routes (e.g. map **point inspect**) remain **synchronous** unless product explicitly moves them to jobs later.

---

## 8. Platform limits (must align in implementation)

| Limit | Implication |
|-------|-------------|
| **Cloud Tasks HTTP `dispatchDeadline`** | Default **10 minutes**; configurable from **15 seconds to 30 minutes** per HTTP task attempt ([Task resource](https://cloud.google.com/tasks/docs/reference/rest/v2/projects.locations.queues.tasks#Task)). |
| **Worker Cloud Run request timeout** | Up to **1 hour** for services, but Tasks **waits at most 30 minutes** per HTTP attempt — **effective ceiling** for a single task delivery is **30 minutes** unless the pattern changes. |
| **Longer work** | If a single unit of work can exceed that, use **Cloud Run jobs**, **chunked tasks**, or **multi-stage** jobs ([Cloud Run — executing asynchronous tasks](https://cloud.google.com/run/docs/triggering/using-tasks)). |

**Implementation rule:** Set **`dispatch_deadline`** from **`WORKER_HTTP_DEADLINE_SECONDS`** (same value Terraform uses for the worker Cloud Run request timeout, capped at **1800s**, Cloud Tasks’ per-attempt maximum). The worker treats a **`running`** lease as stale when **`updated_at`** is at least that many seconds old (plus optional small **`WORKER_STALE_RUNNING_GRACE_SECONDS`**, default **0**) so a **retry soon after** an attempt timeout can reclaim instead of skipping as “fresh.”

---

## 9. Abuse, cost, and reliability

### 9.1 Abuse and cost

- **Per-user / per-project rate limits** on enqueue endpoints (e.g. **429**) to reduce **queue flooding** and **denial-of-wallet**.
- **Optional cap** on concurrent **`running`** jobs per project (reject enqueue when over cap).
- Queue **`max_dispatches_per_second`** and **`max_concurrent_dispatches`** tuned to protect downstream systems.
- **Worker `max_instances`** low for MVP (e.g. **1**) to cap parallel spend; document tradeoff (latency under burst).

### 9.2 Partial failure and artifacts

- **Retry-safe** writes: use **temporary** object names or **staging** prefixes, then **atomic** “promote” (e.g. manifest file or final rename pattern) so retries do not leave **half-written** “latest” artifacts.
- **Pickle / model loading:** treat uploaded artifacts as **untrusted** unless validated; follow existing upload validation; prefer **hash / version** pins in metadata where feasible (see ML artifact principles if applicable).

### 9.3 Observability

- Monitor **queue depth**, **task failure rate**, worker **5xx**, jobs **stuck in `running`** beyond a threshold.
- **Audit** fields: `created_by`, `created_at`, optional **correlation id** in job doc and logs.

### 9.4 Cost expectations (light / MVP traffic)

- **Cloud Run workers:** With **`min_instances = 0`**, no standing cost when idle; spend is **CPU/memory-seconds** and **requests** while jobs run. A **lighter staging** worker reduces cost per second of work vs prod.
- **Cloud Tasks:** Charged per **operations** (enqueue, delivery attempts, etc.); volume is tiny for rare admin jobs — see [Cloud Tasks pricing](https://cloud.google.com/tasks/pricing). Typically **small** relative to Run for this use case.
- **Firestore:** Extra job writes are minor unless enqueue volume is high.
- **Egress:** Keep queue, Run, GCS, and Firestore in the **same region** where possible to avoid cross-region egress surprises.
- **Risk:** **Retry storms** or **accidental tight loops** enqueueing tasks — mitigate with queue **rate limits**, **app-level 429**, and **idempotent** workers.

---

## 10. Development environment and dispatch abstraction

### 10.1 Docker Compose (local)

- Add a **`worker`** service (same image/build as backend, separate port, worker FastAPI app), shared **`./data`**, same **Firestore + Auth emulator** env as API where applicable.
- **Security:** the local bypass POSTs to the worker **without OIDC**. Set **`WORKER_INTERNAL_SECRET`** on API + worker and send header **`X-HSM-Worker-Secret`** (see settings). Keep the worker port **internal** to Compose (or trusted networks) only; omit the secret only in tests or isolated sandboxes.

### 10.2 Two dispatch modes — **one code path in routers**

**Requirement:** Route handlers must **not** sprawl with `if USE_CLOUD_TASKS` / duplicated workflows. **Staging and production** use **Cloud Tasks** only; **local** may bypass Tasks.

**Pattern:**

1. **Settings** (e.g. `pydantic-settings`): e.g. `use_cloud_tasks: bool`, `environment: Literal["local", "staging", "production"]` (or project-specific enum), plus env-specific `WORKER_BASE_URL`, queue id, OIDC SA email where relevant.
2. **Fail fast at startup:** If `environment` is **`staging`** or **`production`** and `use_cloud_tasks` is **false**, **abort application startup** (misconfiguration). Optionally enforce the same for any non-local deploy.
3. **Single abstraction** — a small module exposes one operation used by all enqueue paths, e.g. `schedule_worker_job(...)` or a **`JobDispatcher`** protocol with:
   - **`CloudTasksDispatcher`:** `CloudTasksClient.create_task` (OIDC, URL, body).
   - **`LocalHttpDispatcher`:** registers a **`BackgroundTasks`** callback that **`httpx.post`s** the **same JSON body** to `http://worker:…` (fire-and-forget after the handler returns **202**).
4. **Wire once:** Resolve the implementation at startup (`lifespan`) or via a **`@lru_cache` / `Depends()`** factory so routers receive **one** callable — **no per-route branching**.
5. **Shared payload:** One typed structure (dataclass / Pydantic) serializes to the task HTTP body for both modes so **worker handlers stay identical**.

**Local (`use_cloud_tasks=false`):** API still creates **`pending`** job and returns **202**; **`LocalHttpDispatcher`** triggers the worker. This path is **not durable** (lost if the API process dies before the background POST runs) — **acceptable for local dev only**.

**Staging / prod (`use_cloud_tasks=true`):** **`CloudTasksDispatcher`** only; validates **IAM, OIDC, retries** end-to-end.

**Caveat:** `BackgroundTasks` runs on the **API** process; keep the “bypass” **impossible** in cloud envs via startup checks, not ad hoc env vars in production.

---

## 11. Red-team-derived requirements (summary)

The following are **explicit requirements**, not optional hardening:

1. **Worker authorization:** OIDC alone is insufficient. Worker **loads `job_id` from Firestore** and **re-validates** that the job is allowed to run (status, kind, ownership/admin).
2. **Transactional claim:** **`pending` → `running`** (and **stale `running`** lease refresh) must be **atomic** so duplicate Tasks deliveries do not double-process active work.
3. **Idempotent completion:** Retries must not **corrupt** artifacts or flip terminal state incorrectly.
4. **Job reads:** **`GET /jobs/{id}`** must **authorize** on every request; use **unguessable** job ids.
5. **Firestore:** Job writes from clients **denied**; server SDK only for job collection (MVP).
6. **IAM:** Worker **private**; **no** public invoker; regular **review** of `run.invoker` bindings.
7. **Logging:** No secrets or raw tokens in logs; sanitize client-visible errors.
8. **Prod:** Dev task bypass **disabled** in production deployments (enforce via **startup validation** of settings, not scattered checks).
9. **Dispatch:** Use a **single dispatcher abstraction** (§10.2); **no** duplicated enqueue logic or env conditionals inside individual route handlers.

---

## 12. Infrastructure (Terraform / CI)

- Enable **`cloudtasks.googleapis.com`** on the GCP project **before** first `createTask` (e.g. `gcloud services enable cloudtasks.googleapis.com --project=PROJECT_ID` or Terraform `google_project_service`). **Verify** in console or `gcloud services list --enabled` — this API is easy to forget and failures are opaque until enqueue.
- **Two queues** (e.g. `background-staging`, `background-prod`), each with **retry** and **rate** configuration appropriate to that env.
- **Invoker service account(s)** per env (or shared where IAM allows); **`google_cloud_run_v2_service_iam_member`** granting **run.invoker** on **`worker-staging`** and **`worker-prod`** respectively (staging Tasks SA → staging worker only, prod → prod).
- **Two worker services:** **`worker-staging`** (typically **lighter** CPU/memory/timeout/`max_instances`) and **`worker-prod`** (heavier as required). Both share the **same** image as their env’s API; **different** container **command/args** for the worker entrypoint.
- **CI:** build **once** per commit; deploy the image to **`api-staging`** and **`worker-staging`** from `main` (or your staging convention), and to **`api-prod`** and **`worker-prod`** on release—each with correct env vars (`WORKER_URL`, queue name, OIDC audience, etc.).

---

## 13. Rollout phases (suggested)

1. Infra: **two** queues, **two** worker services, IAM, env vars, deploy pipeline; production guardrails for task bypass.
2. Backend: align repo with §4.4 (**uv** workspace or single multi-package project); worker app + **one** `kind` end-to-end (enqueue, process, GCS write, Firestore terminal state, authorized job GET).
3. Frontend: poll job status for that flow.
4. Add further `kind` values reusing the same envelope, state machine, and security checks.

### 13.1 Candidate `kind` values (order TBD)

Pick **one** vertical first; expand after the pattern is stable.

| Candidate | Notes |
|-----------|--------|
| **Explainability background sample** (e.g. existing `POST …/explainability-background-sample`) | Often **one** cohesive pipeline (raster → Parquet → GCS); fewer interaction points with **upload session** state — **smaller** first slice for Tasks + worker + poll UX. |
| **Replace environmental COG** (today: `POST …/environmental-cogs` with `upload_session_id`) | **High value** (long-running, many stages: ingest URI → validate COG → **promote** to `driver_cog_path` → derive **band definitions** → **upsert_project** → **reload catalog**; clears explainability background fields). **Larger** lift: many failure paths, **upload session** stage updates (`best_effort_mark` / `best_effort_fail`), must be **idempotent** under Tasks retries (especially around **promote** and catalog writes). Product may still choose this first if admin timeout is the main pain. |

**Current env COG flow (sync, API):** See `replace_project_environmental_cogs` in `backend_api/routers/projects.py` — worker extraction should **reuse** the same core helpers where possible and treat the job doc + Firestore as the authority after enqueue.

---

## 14. References

**Google Cloud**

- [Executing asynchronous tasks (Cloud Run + Cloud Tasks)](https://cloud.google.com/run/docs/triggering/using-tasks)
- [Authenticating service-to-service (Cloud Run)](https://cloud.google.com/run/docs/authenticating/service-to-service)
- [Configure containers for services (command / args)](https://cloud.google.com/run/docs/configuring/services/containers)
- [Create HTTP target tasks (authentication)](https://cloud.google.com/tasks/docs/creating-http-target-tasks)
- [Configure Cloud Tasks queues](https://cloud.google.com/tasks/docs/configuring-queues)
- [Cloud Tasks pricing](https://cloud.google.com/tasks/pricing)
- [Task resource (`dispatchDeadline`)](https://cloud.google.com/tasks/docs/reference/rest/v2/projects.locations.queues.tasks#Task)

**Python / tooling**

- [Using workspaces | uv](https://docs.astral.sh/uv/concepts/projects/workspaces/)
