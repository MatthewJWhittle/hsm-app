# Agent guidance (repository root)

This repository is **full-stack**: FastAPI backend, React frontend, infrastructure docs, and data pipelines that feed the catalog.

- **Frontend-only rules:** see [`frontend/AGENTS.md`](frontend/AGENTS.md).
- **Cross-cutting engineering principles** for model artifacts, rasters, bundles, and serving: **[`docs/ml-artifacts-and-serving-principles.md`](docs/ml-artifacts-and-serving-principles.md)**.

When implementing catalog upload, point inspection, driver rasters, or explanation features, read that doc alongside [Data models](docs/data-models.md) and [Solution architecture](docs/solution-architecture.md).

## Backend guidance (FastAPI)

The backend is a **uv workspace** under `backend/`: shared **`hsm_core`**, HTTP app **`hsm_api`** (`backend_api`), and **`hsm_worker`** (same container image; separate Cloud Run service for the worker). It serves `/api` and integrates with Firestore, Firebase Auth, and object storage. Keep code small, explicit, and easy to reason about.

### Core principles

- Prefer **simple, explicit code** over clever abstractions.
- Keep files and functions **small and focused**.
- Add a new abstraction only when it removes real duplication or clarifies a domain boundary.
- Optimise for **readability and maintainability first**, then performance where evidence suggests it matters.
- Avoid verbose "enterprise" patterns unless the app genuinely needs them.

### Architecture rules

- Follow the existing split between:
  - `routers/` for HTTP route definitions
  - `deps/` for FastAPI dependency providers
  - service/domain modules for business logic
  - schema modules for request/response and internal typed models
- Keep route handlers thin. A route should mainly:
  - parse inputs
  - call dependencies/services
  - map domain outcomes to HTTP responses
- Do **not** put substantial business logic directly in router functions.
- Do **not** make routers talk directly to Firestore, Storage, raster processing, or model-loading code if that logic can live in a service/helper module.
- Reuse the **app factory** and **lifespan** pattern already in place. Initialise long-lived clients/resources there, not ad hoc in endpoints.
- Access shared app resources through dependencies, not global mutable singletons.

### Dependencies and settings

- Use FastAPI `Depends` for:
  - settings access
  - auth / current user resolution
  - service construction / lookup
  - reusable request guards
- Prefer small dependency functions with clear names.
- Keep dependency graphs shallow and readable.
- Use `pydantic-settings` / settings objects for configuration. Do not scatter `os.getenv()` calls across the codebase.
- Read configuration once in settings and pass it through dependencies or app state.

### Schemas and types

- Use Pydantic models for request and response contracts.
- Keep API schemas separate from storage-specific representations where that improves clarity.
- Add type hints everywhere practical.
- Prefer explicit field names and explicit return types.
- Avoid passing around untyped `dict[str, Any]` when a model or typed object would make intent clearer.

### Error handling

- Return consistent, structured API errors.
- Raise `HTTPException` for expected request or auth failures at the API boundary.
- Keep internal exceptions internal; convert them to user-safe HTTP errors at the edge.
- Do not leak stack traces, secrets, raw provider errors, or internal storage paths to clients.
- Validate early and fail clearly.

### Async, I/O, and performance

- Use `async` routes when the work is naturally async.
- If work is blocking or CPU-heavy, do not pretend it is async. Use the correct boundary and keep the event loop unblocked.
- Do not perform long-running CPU-heavy raster/model work inline in a request unless the response is expected to wait for it and the cost is acceptable.
- **Background jobs:** In **staging/production**, durable work uses **Firestore job docs** + **Cloud Tasks** → **worker Cloud Run** (see `docs/background-worker-and-tasks-spec.md`). **`BackgroundTasks` + HTTP** to the worker is **local dev only** (`USE_CLOUD_TASKS=false`), not a substitute for Tasks in cloud.
- Treat FastAPI `BackgroundTasks` as suitable only for small, non-critical follow-up work when you are **not** relying on them for durability.
- Prefer simple request/response flows for synchronous endpoints; use the job pattern when latency or CPU cost requires async processing.

### Auth and security

- Keep Firebase Auth verification on the backend as the source of truth for protected routes.
- Enforce authorisation server-side even if the frontend hides UI affordances.
- Default new write/admin routes to secure-by-default.
- Never trust client-supplied admin flags, ownership flags, or storage paths without server validation.
- Avoid overly broad CORS changes. Make the smallest change that supports the required environment.

### Storage and external systems

- Keep provider-specific logic isolated behind clear functions or service modules.
- Do not mix HTTP concerns with Firestore document shaping, storage path construction, raster validation, or model artifact loading.
- Be careful with file uploads:
  - validate type, structure, and key metadata early
  - stream where sensible
  - avoid unnecessary in-memory copies for large files
- Do not create hidden coupling between Firestore schema, storage layout, and HTTP payloads without documenting it.

### Testing

- Add or update tests for meaningful backend changes.
- Prefer tests at the service/module level for business rules.
- Add API tests for route contracts, auth rules, and error handling.
- Mock external systems at sensible boundaries; do not over-mock internal code.
- For bug fixes, add a regression test where practical.

### What to avoid

- Do not create a generic `utils.py` dumping ground.
- Do not add repository-wide base classes unless there is a strong repeated need.
- Do not introduce a service layer, repository layer, adapter layer, manager layer, and factory layer all for one feature.
- Do not duplicate schema definitions with slightly different names unless there is a clear boundary.
- Do not add caching or extra infrastructure "for later" beyond the documented **Cloud Tasks + worker** pattern when the feature needs it.
- Do not silently broaden scope while making a backend change.

### Preferred change pattern for agents

When adding backend functionality:

1. Identify the domain boundary and the HTTP contract.
2. Extend or add Pydantic schemas.
3. Implement or extend a focused service/helper module.
4. Wire it into a thin router via `Depends`.
5. Add/update tests.
6. Update docs only where the behaviour or integration contract changed.

### Decision rules

- Choose the **simplest design that keeps the codebase tidy**.
- Prefer **one obvious place** for each concern.
- When in doubt, copy the **existing backend patterns** already established in this repo instead of inventing a new style.
