# Implementation plan: issue #91 — cold start + map UX

Parent issue: [#91](https://github.com/MatthewJWhittle/hsm-app/issues/91).  
Evidence baseline: [#90](https://github.com/MatthewJWhittle/hsm-app/issues/90).

## Current bottleneck (summary)

- UI first calls: **`GET /api/projects`** + **`GET /api/models`** in parallel (`frontend/src/App.tsx`).
- The API process cannot serve **any** route until `import backend_api.main` finishes: **`routers.models`** imports **`point_explainability`**, which does **`import shap`** at module load → pulls matplotlib/sklearn/scipy (~**~1.5–2 s+** on dev; **~22 s** to `Started server process` on one staging sample).
- **`point_sampling`** imports **`rasterio`** at module load; **`models.router`** imports **`point_sampling`** at top level for **point** routes and shared types.

## Goals

1. **Catalog routes** (`GET /projects`, `GET /models`) must not require loading **SHAP** (and ideally minimize **rasterio**) at process import time.
2. **Point / explainability / warmup** routes keep correct behavior; first request after cold may pay **lazy** import once.
3. Optionally **warm TiTiler** from the client in parallel with catalog.

## Phase 1 — Lazy `shap` in `point_explainability` (backend, P0)

**Files:** `backend/packages/hsm_api/src/backend_api/point_explainability.py`

**Work:**

1. Remove top-level `import shap`.
2. Add a small helper, e.g. `_lazy_shap()`, that imports `shap` on first use (module-level cache optional).
3. In every function that references `shap` (e.g. `_materialize_shap_explainer_bundle`, `compute_shap_driver_variables`, …), call into `_lazy_shap()` before use.
4. Run **`python -X importtime -c "import backend_api.main"`** from `backend/`; confirm cumulative reduction in `shap` subtree.
5. Run **`uv run --package hsm-api pytest`** (full API tests).

**Risks:** None functional if all call sites updated; watch for **type hints** referencing `shap` (use `TYPE_CHECKING` + quoted strings).

**Acceptance:** Importtime shows **no** `shap` / `matplotlib.pyplot` subtree at `import backend_api.main` time (or only trivial stubs).

## Phase 2 — Trim `models.router` import fan-out (backend, P1)

**Problem:** `backend_api/routers/models.py` imports **`point_explainability`** and **`point_sampling`** at **module** top. Even after Phase 1, **`point_sampling`** still pulls **rasterio** before any handler runs.

**Options (pick one path; can split PRs):**

### 2a — Lazy imports inside `models.py` (minimal structural change)

- Replace top-level `from backend_api.point_explainability import …` with **local imports inside** the route handlers / helpers that need them (`validate_explainability_artifacts_for_model`, `warm_explainability_cache`, point endpoints).
- Same for **`point_sampling`** imports: only import where `inspect_point`, `PointSamplingError`, etc. are used.
- **Con:** `models.py` is large; touch many functions; easy to miss a path.

### 2b — Split routers (cleaner, more files)

- `routers/models_catalog.py` — **read-only** `/models`, `/models/{id}` (list/get) with **only** catalog + deps + visibility.
- `routers/models_mutations.py` or keep **admin** + **upload** + **point** in `models.py` or `models_heavy.py` that imports **point_sampling** / **point_explainability**.
- Wire both in `main.py` with `include_router` and same prefixes.
- **Con:** Larger refactor; must preserve OpenAPI tags and paths.

**Recommendation:** Try **2a** first (measure importtime); if still heavy, do **2b**.

**Acceptance:** `import backend_api.main` does **not** load `rasterio` until a lazy path is triggered (verify with `importtime` + grep for `rasterio` in first 500 lines of output, or runtime test).

## Phase 3 — TiTiler parallel warm (frontend, P2)

**Files:** `frontend/src/App.tsx`, `frontend/src/utils/apiBase.ts` (or `titilerWarmup.ts`)

**Work:**

1. After `catalogReady` (or on `MapComponent` mount), **fire-and-forget** `fetch` to a cheap TiTiler endpoint, e.g.:
   - `GET ${titilerBase().replace(/\/$/, '')}/health` or documented health path for the TiTiler image in use, **or**
   - `HEAD`/`GET` on a minimal cog metadata endpoint if no `/health` exists.
2. **Do not** block `catalogReady` or UI on success; swallow errors.
3. Document the chosen URL in `docs/infrastructure-and-deployment.md` (Cold starts section).

**Acceptance:** Manual check: after cold TiTiler + cold API, first tiles appear sooner than without warm (or TiTiler logs show instance start overlapping catalog window).

## Phase 4 — Lifespan catalog (optional spike, P3)

**Only if** Phase 1–2 still leave readiness dominated by **lifespan** Firestore load.

- Spike: defer full `FirestoreCatalogService._load()` from `lifespan` to first `get_catalog` dependency resolution (with thread-safety / single-flight).
- **Tradeoff:** First `/models` **request** pays full load; **health** may pass earlier.

**Acceptance:** Documented latency comparison; no regression in catalog correctness tests.

## Testing checklist

- [ ] `uv run --package hsm-api pytest` (all packages if touched shared code).
- [ ] `python -X importtime -c "import backend_api.main"` before/after (record in PR).
- [ ] Staging: cold request after scale-to-zero; compare `HSM_*` + `Started server process` timing (#90).
- [ ] Manual: map load, layer switch, point inspect, explainability warmup path.

## Rollout

1. Land Phase 1 behind **main**; deploy **staging** (existing workflow).
2. Validate **staging**; then Phase 2 (or 2a).
3. Phase 3 frontend can ship independently.
4. **Prod** follows release deploy (or release tag) per existing process.

## References

- `frontend/src/App.tsx` — catalog + warmup effects.
- `backend/packages/hsm_api/src/backend_api/routers/models.py` — router import hub.
- `backend/packages/hsm_api/src/backend_api/point_explainability.py` — `import shap`.
- `backend/packages/hsm_api/src/backend_api/point_sampling.py` — `import rasterio`.
