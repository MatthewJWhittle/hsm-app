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
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Development

### Backend

The backend is built with FastAPI and provides:
- `GET /models`, `GET /models/{id}` — catalog (models with artifact paths)
- `GET /models/{id}/point` — point value and driver explanation
- Admin: `POST /models`, `PUT /models/{id}` (auth-gated)
- Authentication (Firebase Auth). Tiles are served by a separate TiTiler service; frontend builds tile URLs from model’s COG path.

### Frontend

The frontend is a React TypeScript application featuring:
- Model/species selector (from `GET /models`)
- Interactive map (MapLibre; tiles via TiTiler)
- Point inspection and interpretation guidance
- Admin route for adding/editing models

## License

This project is licensed under the MIT License - see the LICENSE file for details.