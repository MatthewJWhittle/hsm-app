## High‑Level Specification: Habitat Suitability Visualiser

### 1. Purpose & Scope

* **Objective**: Interactive web app to display habitat suitability model outputs (rasters) and vector overlays (e.g. protected areas, sighting points) for different species.
* **Users**: Ecologists, project managers, decision‑makers.
* **Key Goals**: Fast rendering of large raster datasets; intuitive UI; modern, minimal design.

### 2. Tech Stack

Recommended for solo-dev cost control: **Firebase Hosting + Cloud Run + Firestore + Cloud Storage**. See [Infrastructure and deployment](docs/infrastructure-and-deployment.md) for rationale and guardrails.

* **Frontend**: TypeScript + React built to static files, deployed on **Firebase Hosting** (not Cloud Run—preserves free compute; free SSL and 10 GB hosting). In production, configure Hosting to rewrite `/api` to Cloud Run so the app uses one origin and relative API URLs (e.g. `/api/models`).
* **Backend**: FastAPI as a container on **Cloud Run** — min-instances=0, request-based billing, low max-instances (e.g. 1–2).
* **Database**: **Firestore (Native mode)** for catalog, app state, users; real free tier. Avoid Cloud SQL until demand justifies it.
* **Files**: **Cloud Storage** for COGs and uploads; use a free-tier region (e.g. us-central1) where possible.
* **Raster serving**: COGs in Cloud Storage; tile service via TiTiler on Cloud Run (or same bucket, TiTiler as separate service).
* **Vector data**: GeoJSON or MVT from Cloud Storage.
* **Authentication**: Firebase Authentication (free tier) with OAuth2 flows.
* **Secrets**: Secret Manager in production.
* **Build/images**: Artifact Registry + Cloud Build (free tiers available).
* **Mapping**: MapLibre GL (no Mapbox fees).
* **State management**: React Query or Zustand.
* **Styling**: Tailwind CSS.

### 3. Core Features

1. **Species & Activity Selector**:

   * Multi-field selector (species + activity type) to fetch corresponding HSM raster.
2. **Map Canvas**:

   * Main UI focus, full-screen map similar to Google Maps.
   * Load HSM raster layer for chosen species+activity.
   * Overlay anonymised bat records (as large grid cells/boxes).
   * Toggle and adjust opacity of overlays.
3. **Metadata & Info Panel**:

   * Display model accuracy, key variables, resolution, date.
   * Show raster statistics: min, max, mean.
4. **Analytical Tools**:

   * **Point Query**: Click map to display HSM value at location.
   * **Area Query**: Draw polygon to compute and display average HSM within.
5. **Aggregated Layers** (post-MVP):

   * Compute species richness or combined suitability across multiple species.
   * Flexible layer construction: allow stacking or arithmetic operations on rasters.
6. **Export & Share**:

   * Download map view (PNG).
   * Shareable link preserving map state (layers, zoom).
7. **Admin: Add species and models** (MVP):

   * Allow admins to add new species and register/upload suitability models (COGs) and metadata.
   * Support both **UI** (form + upload for occasional updates) and **API** (for bulk or scripted updates).
   * Restrict to authenticated admin users.

### 4. Architecture

* **API Endpoints** (FastAPI). Resource-oriented; align with [Solution architecture](docs/solution-architecture.md) and [Data models](docs/data-models.md).

  * `GET /models` → list all models (id, species, activity, artifact_root, suitability_cog_path, model_name?, model_version?, driver_config?). One round-trip for catalog and tile URL construction; no separate “get URL” call.
  * `GET /models/{id}` → single model by stable id (full entry). Used when selection changes or for detail view.
  * `GET /models/{id}/raster/metadata` → raster details for legend/extent when needed.
  * `GET /models/{id}/point?lng=&lat=` → point value and optional driver explanation (PointInspection: value, unit?, drivers[]).
  * Tiles: frontend builds TiTiler URL from `model.suitability_cog_path` (TiTiler is a separate Cloud Run service).
  * `GET /vectors/{layer}.geojson` → static vector data
  * `POST /auth/token` → OAuth2 token
  * **Admin:** `POST /models` → create model (body: species, activity, COG upload or path, optional metadata/driver config; backend assigns id, writes artifacts to storage with sensible folder structure, stores artifact_root and paths in DB); `PUT /models/{id}` → update model
* **Frontend Components**

  * `App`: root, routes
  * `MapView`: initialises Mapbox, loads layers
  * Model/species selector: fetches `GET /models`, builds dropdowns from list; selection uses model.id and model.suitability_cog_path for tiles (no second “get URL” request)
  * `LayerControlPanel`: toggles layers, opacity
  * `Legend`: dynamic colour ramp
  * **Interpretation guidance / caveats**: in-app content (panel, modal, or legend) explaining what the map means, that output is relative suitability not proof of presence/absence, and that the tool supports (not replaces) expert judgement (MVP must-have).
  * `ExportButton`: screenshot + share link generator
  * **Admin:** `AdminRoute` or `/admin`: list models (`GET /models`), form to add (`POST /models`) or edit (`PUT /models/{id}`) species, activity, COG (upload or path), optional model name/version; auth-gated

### 4.1 Extensibility

Design choices that make later scope easier (see [Solution architecture §7](docs/solution-architecture.md#7-design-for-extension) for full guidance):

- **API:** Keep `/models` and `/models/{id}` as the only first-class raster resource; add query params (e.g. `?species=`) and optional combined/area endpoints later. Scope inspection by model: `GET /models/{id}/point`, and later `GET /models/{id}/area` for polygon stats.
- **Model:** Add optional fields (driver config, taxon, metadata) as needed; ignore unknown keys in clients. Keep vector overlays as a separate resource and type (e.g. `GET /layers` or `GET /vectors`).
- **Frontend:** Single source of truth for selection (`modelId`; later `comparisonModelId` or `selectedModelIds[]`). Put map state in the URL where possible (`?model=id`, then lat, lng, zoom) for sharing and saved sessions. Layer list component that accepts a list of layer descriptors so it can show raster + vector layers.
- **Storage:** Prefer Firestore (or DB) for catalog so new fields and filters don’t require a new API shape.

### 5. Data Flow

1. App load: frontend calls `GET /models` once → list of models (id, species, activity, suitability_cog_path, …). Build species/activity dropdowns (or single “model” dropdown) from this list.
2. User selects a model (by id or species+activity): frontend already has full model from list, or fetches `GET /models/{id}`. Sets raster tile source from `model.suitability_cog_path` (TiTiler URL). No second “get URL” request.
3. Map component loads raster tiles on zoom/drag (TiTiler as separate Cloud Run service).
4. User clicks map: frontend calls `GET /models/{id}/point?lng=&lat=` → show value and drivers (PointInspection).
5. Vector layers and legend: fetched or computed as needed.

### 6. Performance Considerations

* Use COGs + TiTiler for efficient raster tiling.
* Vector simplification or tiling (TopoJSON or MVT) for large vector datasets.
* Lazy‑load layers.
* Caching: HTTP cache headers on GCS and API responses.

### 7. UI/UX & Styling

* Utility‑first Tailwind CSS.
* Minimal chrome: focus on map, slide‑out panels.
* Responsive: works on desktop and tablets.
* Accessibility: keyboard navigation, ARIA labels.

### 8. Security, DevOps & cost control

* Containerised services (Docker Compose or Kubernetes).
* CI/CD pipeline (GitHub Actions): lint, test, build, deploy.
* Secure storage (GCS IAM roles; Secret Manager for secrets).

**Cost control (solo developer):** Keep GCP infrastructure costs low and predictable so the operator is not personally liable for surprise spend. Full guidance: [Infrastructure and deployment](docs/infrastructure-and-deployment.md).

* Use the **recommended stack**: Firebase Hosting, Cloud Run, Firestore, Cloud Storage (no Cloud SQL, GKE, or VPC connectors at start).
* **Cloud Run**: `min-instances=0`, `max-instances=1` or `2`, request-based billing, small CPU/memory.
* **Region**: Prefer one Tier 1 region (e.g. `us-central1`) for Run, Firestore, and Storage to benefit from free-tier coverage.
* Set **GCP budget alerts** (e.g. 50%, 90%, 100%) and optionally a budget cap; document how to set them in README or ops docs.
* **Document expected cost** (e.g. “typical MVP: £0–low single digits/month at light traffic”) and steps to review usage.

### 9. Next Steps & Refinement

* Map library: **MapLibre GL** (no Mapbox fees); already decided.
* Define colour ramps & classification methods.
* Finalise authentication scope: required for admin; optional for general app access in MVP.
* Sketch wireframes.

---

### 10. High-Level Implementation Steps

#### Phase 1: Local-First PoC Setup

1. **Project Bootstrap with UV**

   * Use `uv` CLI to scaffold FastAPI project: creates `pyproject.toml`, dev/test folders, sample app.
   * Initialise frontend via Vite or CRA template in `frontend/`.
   * Configure separate `backend/` and `frontend/` directories under monorepo.
2. **Containerised Local Dev**

   * Write `Dockerfile` for Python app using slim base; include `uv run` commands.
   * Dockerfile for React with multi-stage build.
   * Define `docker-compose.yml` to orchestrate FastAPI, frontend, TiTiler, and emulators.
3. **Local Data & Mock Services**

   * Store sample COGs and GeoJSON in `data/` and mount into TiTiler container.
   * Use Firebase Emulator Suite (Auth & Firestore) for auth and optional catalog; or JSON index file (e.g. `hsm_index.json`) for catalog to match production Firestore shape when migrating.
4. **FastAPI Development**

   * Develop core endpoints (`/species`, `/tiles`, `/vectors`, `/auth`) with Pydantic models.
   * Implement anonymisation logic locally reading from `data/`.
5. **Frontend Development**

   * Build map components and selectors using MapLibre and Tailwind.
   * Integrate React Query against local FastAPI endpoint.
6. **Analytical Tools**

   * Add Turf.js or @turf/turf for point and area queries.
   * Implement draw controls and compute stats on local data.
7. **Testing & CLI Automation**

   * Use `uv` to manage scripts (lint, test, run).
   * Write pytest and Jest tests; run in Docker Compose.
8. **Documentation & Readme**

   * Document local setup steps, `uv` commands, and Docker Compose usage.

#### Phase 2: Cloud Transition

1. **GCP Resource Configuration**

   * Provision GCS buckets; configure IAM roles.
   * Deploy TiTiler to Cloud Run with bucket integration.
2. **Backend Deployment**

   * Push FastAPI container to Google Container Registry.
   * Deploy to Cloud Run; enable autoscaling and HTTPS.
3. **Frontend Hosting**

   * Build and deploy React app to **Firebase Hosting** (see [Infrastructure and deployment](docs/infrastructure-and-deployment.md); do not use Cloud Run for static frontend).
4. **Service Integration**

   * Update environment variables to point to production GCS, **Firestore**, and Firebase Auth (use Firestore for catalog/app data; avoid Cloud SQL for cost control).
5. **CI/CD Pipeline**

   * Use GitHub Actions to build, test, and deploy both services on merge.
6. **Monitoring & cost control**

   * Enable Cloud Monitoring for health and errors.
   * **Mandatory:** Set GCP budget alerts (and optional cap) before significant use; document in repo how to set them. Prefer Cloud Run scale-to-zero and free-tier services to keep solo-developer cost predictable and low.

---

### 11. Best practice code guidelines

Use commands to set up dependencies and configuration so that everything is configurable. Record the commands in the README.

* **Modular Structure**: Split code into clear modules, avoid monolithic files.
* **Type Safety**: Use strict TypeScript typings and Pydantic models for API schemas.
* **Container Best Practices**:

  * Keep images lean (use Python slim base image).
  * Leverage multi-stage builds for frontend assets.
* **Error Handling**: Centralised error middleware in FastAPI; user-friendly error messages on frontend.
* **Testing**:

  * Write tests for all API endpoints and core React components.
  * Mock external services (GCS, TiTiler) in tests.
* **Performance**:

  * Debounce user inputs for selectors.
  * Memoise React components where useful.
* **Documentation**:

  * Docstrings for Python functions; JSDoc for key frontend modules.
  * Auto-generate OpenAPI spec from FastAPI.
* **Security**:

  * Validate and sanitise all client inputs.
  * Set HTTP security headers via middleware.

---

### 12. Local Development Setup

* **Monorepo & Docker Compose**: Define a `docker-compose.yml` to spin up:

  * FastAPI service with live-reload (using `uvicorn --reload`).
  * React frontend with `npm start` or `vite` server.
  * Local TiTiler container pointing to a dev bucket or local COGs folder.
  * (Optional) Firestore emulator and Firebase Auth emulator for auth flows.
* **Environment Configuration**:

  * Use `.env` files (`.env.development`) for local credentials and endpoints.
  * Leverage Google Cloud SDK auth for local CLI if needed.
* **Local COGs & Vector Data**:

  * Keep a small sample dataset in `data/` for rapid iteration.
  * Configure TiTiler to serve from `./data` folder in Docker Compose.
* **Mock Services**:

  * Use the Firebase emulator suite for Auth and Firestore (catalog can live in Firestore emulator or in a JSON index file for local dev).
* **Tooling & Scripts**:

  * Add NPM scripts (`npm run dev`) to start both frontend and backend concurrently.
  * Provide Makefile targets (e.g. `make dev`, `make test`).
* **Hot-Reload & Watchers**:

  * Backend: Uvicorn's `--reload` flag.
  * Frontend: Vite/CRA's hot module replacement.
* **Local Debugging**:

  * Expose ports in Docker Compose (e.g. 8000 for API, 3000 for UI, 8080 for TiTiler).
  * Mount code directories for live edits.
* **Documentation**:

  * README with setup steps: prerequisites, `docker-compose up`, accessing services.
  * Troubleshooting tips for common errors.

