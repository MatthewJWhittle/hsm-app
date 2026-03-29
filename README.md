# Bat Habitat Suitability Conservation Tool

An interactive web application for visualizing habitat suitability model outputs and vector overlays, built to support conservation practitioners, ecologists and bat groups.

## Purpose

The project aims to provide stronger tools for:

- understanding habitat suitability across the landscape
- targeting survey effort more effectively
- interpreting sites in their wider ecological context
- prioritising conservation attention

The application is intended as a **decision-support tool**, not a decision automation tool.

### Product documentation

Product and solution design docs live in [`docs/`](docs/). See [docs/README.md](docs/README.md) for overview and reading order.

1. [Problem statement](docs/problem-statement.md) — the conservation and decision-support problem
2. [Outcomes and product goal](docs/outcomes-and-product-goal.md) — intended outcomes and product goal
3. [Users and use cases](docs/users-and-use-cases.md) — main users, needs and priority use cases
4. [Product principles](docs/product-principles.md) — principles for scope, design and decision-making
5. [MVP scope](docs/mvp-scope.md) — smallest useful version of the product
6. [Solution architecture](docs/solution-architecture.md) — high-level architecture linking product goals to technical design  
7. [Data models](docs/data-models.md) — data models (Model, catalog, PointInspection, DriverVariable)  
8. [Infrastructure and deployment](docs/infrastructure-and-deployment.md) — how to run and deploy the app (GCP stack, cost guardrails, what to avoid)

## Features

- Interactive map visualization of habitat suitability rasters (COGs added via admin upload)
- Species and model selection (stable id per model; catalog in Firestore)
- Point inspection and simple driver explanation
- Interpretation guidance and caveats
- Admin: add species and upload/register models (COGs) via UI or API
- Vector overlay support (planned); export and sharing (planned)

## Tech Stack

- **Frontend**: React + TypeScript, deployed on Firebase Hosting (production: `/api` rewrites to backend)
- **Backend**: FastAPI (Python) on Cloud Run
- **Tiles**: TiTiler as a separate Cloud Run service (own container)
- **Database**: Firestore (catalog, artifact paths)
- **Storage**: Cloud Storage (COGs and uploads)
- **Mapping**: MapLibre GL
- **Styling**: Tailwind CSS
- **State management**: React Query
- **Authentication**: Firebase Auth

## Project Structure

```
hsm-app/
├── backend/           # FastAPI application (.gitignore for Python/uv)
├── frontend/          # React + TypeScript (.gitignore for Node/Vite); `npm run build` → dist/
├── data/              # Sample data (see data/.gitignore)
├── firebase.json      # Firebase Hosting (serves frontend/dist), emulators, Firestore rules path
├── firestore.rules
├── docker-compose.yml
└── .gitignore         # Repo-wide only; backend/ and frontend/ add their own
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Google Cloud SDK (for deployment)

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd hsm-app
   ```

2. Start the development environment:
   ```bash
   docker-compose up --build -V
   ```
`-V` : Recreate anonymous volumes instead of retrieving data from the previous containers.
This make Vite work - don't remove it.

The backend service mounts an **anonymous volume** on `/app/.venv` (same idea as the frontend’s anonymous `/app/node_modules`), so the bind-mounted repo does not overlay the container venv with your Mac `.venv`. The startup command runs `uv sync --no-dev` into that empty mount (runtime deps only; no pytest). The image **COPY** is scoped to `pyproject.toml`, `uv.lock`, and `backend_api/` only — not tests or the whole repo root.

The **frontend** waits until the **backend healthcheck** passes (`GET /health`) so Vite does not proxy `/api` to the API before `uvicorn` is listening (avoids `ECONNREFUSED` on first load).

Optional Firebase/JOSE dependencies live under `[project.optional-dependencies] auth` in `backend/pyproject.toml`; install with `uv sync --extra auth` when you add those imports.

**If Docker reports `no space left on device`:** see [Root cause: Docker “no space left on device”](#root-cause-docker-no-space-left-on-device) below.

3. Access the applications:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - TiTiler (local tiles): http://localhost:8080

**Firebase Emulator Suite (Docker Compose)** — the **`firebase-emulators`** service starts with the rest of the stack (image: `docker/firebase-emulators/Dockerfile`: Java 21 + Node 20 + `firebase-tools`). **First boot** can take a minute while emulator JARs download; later boots reuse the **`firebase_emulator_cache`** volume.

| URL / port | Service |
|------------|---------|
| http://localhost:4000 | Emulator Suite UI |
| **4400** | Emulator Hub (required for UI; SPA calls this from the browser) |
| **4500** | Emulator logging |
| **8085** | Firestore emulator API |
| **9150** | Firestore Emulator UI websocket |
| **9099** | Auth emulator |

Ports avoid clashing with TiTiler on **8080**. If the Firestore page at `/firestore/...` is **blank**, ensure **4400**, **4500**, **8085**, and **9150** are published (`docker-compose.yml`). **`firebase.json`** must bind each emulator to **`0.0.0.0`** (see `emulators.hub`, `emulators.firestore`, etc.); a root-only `host` is not enough—otherwise processes may listen on **127.0.0.1** inside the container and the browser cannot reach mapped ports. If it still fails, check the browser **Network** tab for **`ERR_CONNECTION_REFUSED`** to **8085** or **9150**, or the **Console** for `Failed to fetch`.

**Default (Docker Compose):** the backend sets **`FIRESTORE_EMULATOR_HOST=firebase-emulators:8085`** so the Firestore client uses the emulator. **`GOOGLE_CLOUD_PROJECT`** defaults to **`hsm-dashboard`** in **`backend_api/settings.py`** (match **`.firebaserc`**). The catalog lives in the Firestore **`models`** collection (constant **`MODELS_COLLECTION_ID`** in **`catalog_service`**). **`GET /models`** reads from Firestore (the frontend still calls only the API).

**`GET /models`** returns **`[]`** until the **`models`** collection has documents. Populate it by **seeding** from JSON (below), **export/import**, or the Emulator UI. Dev seeding lives under **`backend/scripts/`** (`seed_firestore_emulator.py`, `firestore_seed_catalog.py`), not in the API package.

**Seed Firestore from the JSON catalog (repeatable):** with emulators up, from the repo root:

```bash
cd backend && uv run python scripts/seed_firestore_emulator.py \
  --catalog ../data/catalog/firestore_models.json
```

Set **`FIRESTORE_EMULATOR_HOST=127.0.0.1:8085`** when the emulator is bound on the host (e.g. Docker Compose port mapping). From inside the backend container:

```bash
docker compose exec backend sh -c \
  'export FIRESTORE_EMULATOR_HOST=firebase-emulators:8085 GOOGLE_CLOUD_PROJECT=hsm-dashboard \
   && uv run python scripts/seed_firestore_emulator.py --catalog /data/catalog/firestore_models.json'
```

Restart the backend after seeding if it already started with an empty catalog.

**Save emulator data to disk (export) and reload it on the next start:** Compose mounts **`./data`** at **`/workspace/host-data`**. The import/export directory must be a **subfolder** inside that mount (e.g. **`firestore-seed/`**). **Do not** bind-mount only `data/firestore-seed` as the container path for export (e.g. mapping it alone to `/workspace/host-data/firestore-seed`) — that makes the export path the **mount root** again and **`firebase emulators:export`** fails with **`EBUSY: resource busy or locked, rmdir`** (not a Unix permission bit issue). While the emulators are running, write a snapshot under **`/workspace/host-data/firestore-seed`**. Use the **same** Firebase CLI as the container (`firebase-tools@15.12.0` in `docker/firebase-emulators/Dockerfile`) and the **same project** as `emulators:start` (`.firebaserc` default: **`hsm-dashboard`**):

```bash
mkdir -p data/firestore-seed

docker compose exec -w /workspace firebase-emulators \
  firebase -P hsm-dashboard emulators:export /workspace/host-data/firestore-seed --force
```

That directory gets **`firebase-export-metadata.json`** plus **`firestore_export/`** (and auth data if you use Auth). **`docker-compose.yml`** always passes **`--import=/workspace/host-data/firestore-seed`**; if the folder is empty or has no export metadata, Firebase logs a warning and starts with no imported data (then use the Python seed script or the Emulator UI).

**If export says it cannot find running emulators:** run the command **inside** the `firebase-emulators` service (as above), not a different `firebase` on your Mac. Include **`-P hsm-dashboard`** and **`-w /workspace`** so the CLI resolves **`firebase.json`**. For more detail: append **`--debug`** to the `firebase` command. To export from the **host** instead, use **`npx firebase-tools@15.12.0`** with the repo root as cwd and emulators reachable on **`127.0.0.1:4400`** (hub).

You can commit the export under **`data/firestore-seed/`** so teammates get the same seed, or keep it local-only.

**Auth (test users):** the Auth emulator starts with **no users**. You can add them in the **Emulator UI** (http://localhost:4000 → Authentication) or via your app once the frontend uses `connectAuthEmulator`. You do **not** need real Google accounts or Firebase Console for the emulators. For **admin routes** (future), you will use test users + custom claims or an allowlist—Console setup applies to **production** only.

**Without Docker:** you can still run **`firebase emulators:start`** on the host; point the backend at **`FIRESTORE_EMULATOR_HOST=127.0.0.1:8085`** (host) or **`host.docker.internal:8085`** (backend in Docker, emulators on host).

**Firebase Hosting deploys** the Vite production build at **`frontend/dist`** (build with `cd frontend && npm run build`). GitHub Actions run the same build before `firebase deploy`.

## Development

### Local prototype (this repo today)

For local development, [`data/catalog/firestore_models.json`](data/catalog/firestore_models.json) is a **Firestore-shaped JSON snapshot** (one object per document in **`documents[]`**, document id = `Model.id`) used to **seed** the emulator via **`backend/scripts/seed_firestore_emulator.py`**, not loaded by the API. Regenerate it from COGs under `data/hsm-predictions/cog/` with [`scripts/generate_hsm_index.py`](scripts/generate_hsm_index.py) (also invoked at the end of [`scripts/convert_to_cog.sh`](scripts/convert_to_cog.sh)) — a **temporary** helper until COGs are managed via an admin API. Offline validation of that JSON shape uses **`backend_api.catalog.catalog_to_models`** (see [`docs/data-models.md`](docs/data-models.md)).

**Backend (FastAPI)**

- `GET /models` — list catalog entries from Firestore ([`Model`](docs/data-models.md)); **`503`** if Firestore could not be read or a document fails schema validation; **`200`** with **`[]`** if the collection is empty
- `GET /models/{id}` — single model (**`404`** if unknown; **`503`** when the catalog could not be loaded or failed validation)

The **`FirestoreCatalogService`** in `backend_api.catalog_service` implements the **`CatalogService`** protocol (injected via FastAPI `Depends`). **`GOOGLE_CLOUD_PROJECT`** (default **`hsm-dashboard`**) and **`FIRESTORE_EMULATOR_HOST`** (dev only) are read from the environment.

**Frontend**

- Model dropdown from `GET /models` via the Vite dev proxy (`/api` → backend). Locally, set `VITE_API_BASE=/api` (default). For production builds served without the proxy, set `VITE_API_BASE` to the full API origin if needed.
- Raster tiles: MapLibre requests TiTiler at `VITE_TITILER_URL` (default `http://localhost:8080`) using `file:///…` paths that match the `./data` mount in Docker and Compose.

**Docker Compose (frontend dev server)**

- The Vite proxy target must reach the API from the frontend container: `API_PROXY_TARGET=http://backend:8000` is set in Compose. Local `npm run dev` without Docker uses `http://127.0.0.1:8000` by default.

**Backend tests**

```bash
cd backend && uv run pytest
```

If you run **`uvicorn` outside Docker** with the emulator on the host, set **`FIRESTORE_EMULATOR_HOST=127.0.0.1:8085`**. Omit **`FIRESTORE_EMULATOR_HOST`** in production so the client uses real Firestore.

### Next steps

Firestore-backed catalog, Firebase Auth, `GET /models/{id}/point`, and admin `POST/PUT /models` are described in [`application-spec.md`](application-spec.md). The frontend will keep using relative `/api/...` URLs behind Firebase Hosting rewrites to Cloud Run.

### Root cause: Docker “no space left on device”

That message means the **storage backing Docker’s writes** refused the operation because **there was not enough free space left** (or the filesystem hit a quota). On Docker Desktop for Mac, writes usually go to Docker’s **Linux VM disk image**; it has a **fixed maximum size** in Settings → Resources, and it can fill up from images, build cache, containers, and volumes.

The path shown in the error (for example under `/var/lib/docker/volumes/...` or a file inside `node_modules` or a Python package) is **where the write failed**, not proof that *that file* is misconfigured. Large dependencies only explain **why the next write needed many megabytes**; they are not the root cause. The root cause is **insufficient free space** in Docker’s disk image and/or on the host drive.

**What to do:** check free space on the Mac; open Docker Desktop → **Settings → Resources** and review **disk image size** and usage; run `docker system df` and reclaim space with `docker system prune` (and remove unused volumes only if you accept losing that data). Increasing the disk image limit or freeing host disk fixes the issue; trimming `COPY` in Dockerfiles does not fix a full disk.

## License

This project is licensed under the MIT License - see the LICENSE file for details.