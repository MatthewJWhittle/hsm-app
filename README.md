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
├── backend/           # FastAPI application
├── frontend/         # React TypeScript application
├── data/            # Sample data for development
└── docker/          # Docker configuration files
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

3. Access the applications:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - TiTiler (local tiles): http://localhost:8080

## Development

### Local prototype (this repo today)

For local development, the catalog is a JSON index on disk (see `data/hsm_index.json`), built from COGs under `data/hsm-predictions/cog/` via [`scripts/generate_hsm_index.py`](scripts/generate_hsm_index.py) (also invoked at the end of [`scripts/convert_to_cog.sh`](scripts/convert_to_cog.sh)). The backend loads that file at startup (`HSM_INDEX_PATH`, default `/data/hsm_index.json` in Docker).

**Backend (FastAPI)**

- `GET /hsm/options` — species, activities, and items (`species`, `activity`, `cog_path`)
- `GET /hsm/url?species=&activity=` — resolves `cog_path` for the TiTiler layer

**Frontend**

- Species and activity dropdowns from `/hsm/options`; raster path from `/hsm/url`
- MapLibre + TiTiler at `http://localhost:8080` using paths that match the mounted `./data` volume

### Target production API

The product docs and [`application-spec.md`](application-spec.md) describe the API to implement next: Firestore-backed catalog, Firebase Auth, and resource-oriented routes such as `GET /models`, `GET /models/{id}`, `GET /models/{id}/point`, plus admin `POST/PUT /models`. The frontend will use relative `/api/...` URLs behind Firebase Hosting rewrites to Cloud Run.

## License

This project is licensed under the MIT License - see the LICENSE file for details.