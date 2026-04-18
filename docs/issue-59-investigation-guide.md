# Issue #59 investigation guide

**Issue:** [Investigate staging 502/504 on environmental COG replace after memory increase](https://github.com/MatthewJWhittle/hsm-app/issues/59)  
**Branch:** `issue-59-staging-502-environmental-cog` (or current working branch)

This document consolidates the plan for reproducing and fixing intermittent **502** (browser) / **504** (~60s, Cloud Run) failures on **`POST /api/projects/{project_id}/environmental-cogs`** against **staging**, plus risks, mitigations, and how to validate fixes in code.

---

## 1. Problem summary

- After increasing `api-staging` memory, environmental COG **replace** from the admin flow can still fail with a Google **502** page and backend **504** (~60s latency).
- Evidence points to **request timeout** behavior distinct from earlier **OOM** (#56): e.g. 504 at ~60s on a given revision.
- **Goal:** Attribute failure to a **phase** (ingest, validate, persist, derive, background generation), then change code or deployment so expected workloads complete within limits **or** return explicit structured errors—with clear logs.

---

## 2. Why staging (not only local Docker)

| Surface | What it reproduces |
|--------|---------------------|
| **Staging (`api-staging`, often via dev Hosting)** | Cloud Run **request deadline**, real **GCS**, real **Firestore**, **Hosting → `/api` rewrite**, gateway **502 vs 504** behavior, cold starts, production-like latency. |
| **Local Docker Compose** | Same **application code path** and heavy steps (raster/validate/derive) with **emulators + local storage**—good for **logic and CPU/memory**, **not** the full gateway timeout story. |

**Conclusion:** Use **staging for authoritative reproduction** of 502/504; use **local** to **validate mechanisms** and **automated tests** once a phase is identified.

---

## 3. Staging test plan

### 3.1 Preconditions

- Access to sign in on **dev Hosting** (`hsm-dashboard-dev` → `/api` → `api-staging`; see [`deployment-runbook.md`](./deployment-runbook.md)).
- Read access to **Cloud Logging** for project `hsm-dashboard` and ability to inspect **Cloud Run** `api-staging` (revision, timeout, memory).
- **Baseline snapshot** before each session: revision name, request timeout, memory/CPU, traffic split (100% one revision when possible).

### 3.2 Repeatable flow

For each test run, use the **same** sequence and record metadata:

1. Authenticate (browser or script); obtain a **Firebase ID token** if calling the API directly.
2. Create or select a **disposable** test project (see §5—shared Firestore with prod).
3. Upload / attach models using the **same path as admin** (including signed-url flow if used).
4. Call **`POST /api/projects/{project_id}/environmental-cogs`** (multipart or `upload_session_id` per API).
5. Record: **UTC time**, `project_id`, **payload size**, **HTTP status**, **headers** (`x-request-id`, `trace`, `x-cloud-trace-context` if present), and whether the **browser showed 502** while logs showed **504**.

Vary **COG size** (small vs representative) to see correlation with time or always ~60s.

### 3.3 Log correlation

For each failure or slow success:

1. Filter `api-staging` logs around the timestamp.
2. Open the **request log** for the matching **trace** / request id.
3. Align **phase logs** (`project_replace_env_cog_*` in `backend_api/routers/projects.py`) with **total latency**.
4. Note **revision**; avoid interpreting results across mixed revisions during deploys.

### 3.4 Controlled experiments

Change **one** thing at a time (same inputs):

- **Direct Cloud Run URL** vs **dev Hosting** (isolate proxy vs handler).
- **After** a config change (e.g. timeout): redeploy, confirm revision, retest.
- Avoid testing mid-rollout unless comparing revisions intentionally.

### 3.5 Acceptance (from #59)

- No browser-facing **502/504** for **expected-size** environmental COG replacement tests on staging, **or** a documented gap with mitigation plan.
- Requests complete within configured timeout **or** return **structured API errors** with **phase context**.
- Logs clearly distinguish **timeout vs validation vs storage** failures.

### 3.6 Smoke checks and cold starts

- **`min-instances=0`** (typical for staging) means the **first request after idle** can spend **many seconds** on Cloud Run **cold start** before your handler runs. That time **counts toward the request deadline** from the client’s perspective.
- **Symptom:** Scripts or `curl` with a **short** `--max-time` (e.g. 15s) can see **timeouts or zero bytes** even when the service is healthy; a second request may return **200** in under a second.
- **Mitigation:** For any automated or CLI probe of staging, use a **generous timeout on the first call** (e.g. 60–120s), or send a **cheap warmup** (`GET /api/openapi.json`) before timing the scenario under test.
- **Public read path:** `GET /api/models` returns **200** without auth (catalog read). **`POST /api/projects/{id}/environmental-cogs`** correctly returns **401** without a Bearer token—use that to verify routing without touching Firestore writes.

---

## 4. Local Docker role

- **Use for:** Debugging **which phase dominates** CPU/time; catching regressions in validate/derive/background **logic**; **pytest** with real tiny COGs.
- **Do not expect:** Identical **60s Cloud Run 504** or Google **502** HTML; emulate the **mechanism** (e.g. synchronous background step too heavy), not the platform status line.

Optional middle ground: run the API with **real GCP** env (not emulators) in Docker—closer I/O, still **no** Cloud Run deadline unless simulated.

---

## 5. Risks and mitigations (staging)

| Risk | Mitigation |
|------|------------|
| **Dev/staging uses shared Auth/Firestore with prod** (per runbook) | Use **dedicated test users** and **obviously non-prod** project names/IDs; never reuse production catalog IDs carelessly. |
| **Accidental impact / clutter** | Least-privilege GCP access; **clean up** test projects/assets when done. |
| **Cost / quota** | Start small; cap repetition; scale payload size deliberately. |
| **Secrets exposure** | Short-lived tokens; env vars only; never commit tokens or SA keys. |
| **Wrong conclusion** | Every run: **revision + trace**; compare Hosting vs direct Run when ambiguous. |
| **Deploy noise** | Test when traffic is on a **single** revision. |
| **Cold start + short client timeout** | First request after idle can take **15–25s+** before first byte; do not mistake that for a broken route or a handler timeout. Warm up or lengthen client timeouts (§3.6). |

---

## 6. Validating a suspected root cause

1. **Staging:** Same request **before/after** change; same revision semantics; trace shows time in **one phase** matching timeout.
2. **Local:** Reproduce **dominant phase** with real small/large fixture or **targeted mocks** (e.g. slow background function) so CI can assert behavior.
3. **Do not** require local HTML 502 to match production; require the **same bottleneck** to disappear when the fix is applied.

---

## 7. Fixing in code (typical directions)

Depends on validated cause:

- **Too much synchronous work** in one request (e.g. explainability background in the same handler): defer to **async job / second step**, reduce work, or narrow sampling—**not** only “raise Cloud Run timeout” unless product accepts that.
- **Slow storage:** fewer round trips, retries, or moving bytes off the hot path.
- **Opaque failures:** **Structured errors** + **phase** in response/logs (#59 criteria).

Preserve or extend **phase logging** so staging remains diagnosable.

---

## 8. Testing strategy (thorough but realistic)

| Layer | Purpose |
|-------|---------|
| **Unit / behavior** | Order of phases; on failure in validate/persist/derive, later steps **not** run; correct status/detail codes. Use **mocks** to simulate **slow** steps if adding deadlines or async behavior. |
| **Integration (real tiny COG)** | Happy path with **minimal real file** and local storage—catches real validate/derive regressions. Existing patterns: `admin_client_proj`, tests under `backend/tests/`. |
| **Staging** | Confirms **504/502** resolved under real deadline and Hosting path. |

**Note:** Reproducing **exact** 60.000s 504 in pytest is brittle; tests should lock in **“heavy step not blocking response”** (or **respects budget**), while **staging** proves Cloud Run behavior.

---

## 9. Related references

- [`docs/deployment-runbook.md`](./deployment-runbook.md) — `api-staging`, dev Hosting, shared Firebase.
- [`infra/architecture.md`](../infra/architecture.md) — API staging topology.
- Backend route: `replace_project_environmental_cogs` in `backend/backend_api/routers/projects.py`.
- Related issue: **#56** (OOM during environmental COG ingest).

---

## 10. Checklist (quick)

- [ ] Snapshot `api-staging` revision, timeout, memory.
- [ ] **Warmup or long timeout** on first staging request after idle (§3.6).
- [ ] Run repeatable environmental COG replace; capture trace + headers.
- [ ] Correlate logs to **phase**; note 502 vs 504 vs app error.
- [ ] (If needed) Compare Hosting vs direct Cloud Run.
- [ ] Reproduce **mechanism** locally or with tests.
- [ ] Implement fix + **unit/integration** tests.
- [ ] Redeploy staging; repeat scenario; confirm acceptance criteria.

---

## 11. Dry-run log (staging + local)

*Purpose: exercise the investigation workflow once without admin credentials; note surprises for future runs.*

**Date:** 2026-04-18  

### 11.1 Local (Docker + pytest)

| Step | Result |
|------|--------|
| `pytest` — `test_project_band_definitions.py`, `test_upload_sessions.py`, `test_env_cog_band_inference.py` | **25 passed** (~5s). |
| `GET http://127.0.0.1:8000/health` | **200**, ~3ms |
| `GET http://127.0.0.1:8000/api/openapi.json` | **200**, ~22ms |
| `GET http://127.0.0.1:8000/api/models` | **200**, ~2ms |

*Pytest emitted Pydantic serializer **warnings** on `test_post_replace_environmental_cog_uses_upload_session` (mock band defs as `dict`); unrelated to staging timeouts but visible in CI output.*

### 11.2 Staging via dev Hosting (`https://hsm-dashboard-dev.web.app`)

| Step | Result |
|------|--------|
| First `GET /api/openapi.json` (after idle, ~25s client cap) | **200**, ~**22s** total time — dominated by **cold start / first byte**, not OpenAPI generation. |
| `GET /api/models` with **15s** timeout (immediately after) | **Client timeout**, 0 bytes — still warming or queue; **too aggressive** for first hit. |
| `GET /api/openapi.json` (60s cap, warm) | **200**, ~**0.24s** |
| `GET /api/models` ×2 (warm) | **200**, ~**0.19s** each |
| `POST /api/projects/fake-project-id/environmental-cogs` (no body, no auth) | **401** quickly — confirms **admin path is protected** without creating data. |

### 11.3 Not run (credentials / risk)

- No **Firebase ID token**, **no** `POST` environmental COG replace, **no** uploads, **no** Cloud Logging correlation — avoids touching shared Firestore with real writes from automation.

### 11.4 Takeaways added to this guide

1. **Always account for cold start** when timing staging from CLI or scripts (#59 timeouts are ~60s total; burning 20s+ on cold start leaves less headroom for handler work).  
2. **Smoke with warmup:** e.g. one uncached `GET /api/openapi.json` before measuring the operation under test.  
3. **Unauthenticated POST** to environmental-cogs is a safe **routing/auth** check (**401**); full replace testing still requires a **dedicated test user** and disposable project (§5).
