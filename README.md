# Habitat Suitability Model Visualiser

An interactive web application for visualizing habitat suitability model outputs and vector overlays for different species.

## Features

- Interactive map visualization of habitat suitability rasters
- Vector overlay support (protected areas, sighting points)
- Species and activity type selection
- Raster statistics and metadata display
- Point and area query tools
- Export and sharing capabilities

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript
- **Mapping**: MapLibre GL
- **Raster Serving**: Cloud-Optimized GeoTIFFs (COGs) via TiTiler
- **Styling**: Tailwind CSS
- **State Management**: React Query
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
   docker-compose up
   ```

3. Access the applications:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Development

### Backend

The backend is built with FastAPI and provides:
- REST API endpoints for species data
- Raster tile serving via TiTiler
- Vector data endpoints
- Authentication services

### Frontend

The frontend is a React TypeScript application featuring:
- Interactive map interface
- Species selection
- Layer controls
- Analysis tools

## License

This project is licensed under the MIT License - see the LICENSE file for details.