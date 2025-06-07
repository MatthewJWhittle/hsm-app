## High‑Level Specification: Habitat Suitability Visualiser

### 1. Purpose & Scope

* **Objective**: Interactive web app to display habitat suitability model outputs (rasters) and vector overlays (e.g. protected areas, sighting points) for different species.
* **Users**: Ecologists, project managers, decision‑makers.
* **Key Goals**: Fast rendering of large raster datasets; intuitive UI; modern, minimal design.

### 2. Tech Stack

* **Backend**: FastAPI running on Google Cloud Run
* **Frontend**: TypeScript + React deployed via Firebase Hosting or Cloud Run
* **Mapping Library**: MapLibre GL (no Mapbox fees)
* **Raster Serving**: Cloud‑Optimised GeoTIFFs (COGs) stored in Google Cloud Storage; tile service via open‑source TiTiler on Cloud Run
* **Vector Data**: GeoJSON or MVT served from Cloud Storage or Cloud Run
* **Authentication**: Firebase Authentication (free tier) with OAuth2 flows
* **State Management**: React Query or Zustand
* **Styling**: Tailwind CSS

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
5. **Aggregated Layers**:

   * Compute species richness or combined suitability across multiple species.
   * Flexible layer construction: allow stacking or arithmetic operations on rasters.
6. **Export & Share**:

   * Download map view (PNG).
   * Shareable link preserving map state (layers, zoom).. Architecture

* **API Endpoints** (FastAPI)

  * `GET /species` → list available species and metadata
  * `GET /species/{id}/raster/metadata` → raster details
  * `GET /tiles/{species}/{z}/{x}/{y}.png` → raster tiles (via titiler)
  * `GET /vectors/{layer}.geojson` → static vector data
  * `POST /auth/token` → OAuth2 token
* **Frontend Components**

  * `App`: root, routes
  * `MapView`: initialises Mapbox, loads layers
  * `SpeciesSelector`: fetches `/species`
  * `LayerControlPanel`: toggles layers, opacity
  * `Legend`: dynamic colour ramp
  * `ExportButton`: screenshot + share link generator

### 5. Data Flow

1. User selects species → frontend requests metadata → sets up raster tile source.
2. Map component loads raster tiles on zoom/drag.
3. Vector layers fetched once or on demand.
4. Legend values computed from metadata or on‑the‑fly sampling.

### 6. Performance Considerations

* Use COGs + titiler for efficient raster tiling.
* Vector simplification or tiling (TopoJSON or MVT) for large vector datasets.
* Lazy‑load layers.
* Caching: HTTP cache headers on S3 and API responses.

### 7. UI/UX & Styling

* Utility‑first Tailwind CSS.
* Minimal chrome: focus on map, slide‑out panels.
* Responsive: works on desktop and tablets.
* Accessibility: keyboard navigation, ARIA labels.

### 8. Security & DevOps

* Containerised services (Docker Compose or Kubernetes).
* CI/CD pipeline (GitHub Actions): lint, test, build, deploy.
* Secure storage (S3 IAM roles).

### 9. Next Steps & Refinement

* Decide on map library (MapLibre vs Mapbox).
* Define colour ramps & classification methods.
* Finalise authentication scope.
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
   * Spin up Firebase Emulator Suite (Auth & Firestore) and optional SQLite/Postgres for metadata.
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

   * Build and deploy React app to Firebase Hosting or Cloud Run.
4. **Service Integration**

   * Update environment variables to point to production GCS, Firestore/Cloud SQL, and Firebase Auth.
5. **CI/CD Pipeline**

   * Use GitHub Actions to build, test, and deploy both services on merge.
6. **Monitoring & Cost Control**

   * Enable Cloud Monitoring, set up alerts.
   * Apply budget alerts and review usage.

---

### 11. Best Practice Code Guidelines Best Practice Code Guidelines

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

  * Use the Firebase emulator suite for Auth and Firestore.
  * Spin up a simple Postgres or SQLite instance for metadata if using Cloud SQL emulator.
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

