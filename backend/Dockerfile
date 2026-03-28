FROM python:3.13-slim

# Rasterio wheels link against libexpat (XML parser used by GDAL stack); slim image omits it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Avoid uv hardlink warnings when cache and /app are on different filesystems (common in Docker Desktop).
ENV UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Dependency metadata only — keeps build context tiny and layer cached.
COPY pyproject.toml uv.lock /app/

# Runtime deps only (no dev/pytest); smallest image and .venv volume.
RUN uv sync --frozen --no-dev

# Application package only — do not COPY tests, scripts, or repo root clutter.
COPY backend_api/ /app/backend_api/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
