FROM python:3.13-slim

# Rasterio wheels link against libexpat (XML parser used by GDAL stack); slim image omits it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Avoid uv hardlink warnings when cache and /app are on different filesystems (common in Docker Desktop).
ENV UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Workspace: lockfile + all member packages (API default CMD; Cloud Run worker overrides command).
COPY pyproject.toml uv.lock ./
COPY packages ./packages

# Non-editable installs: Cloud Run must resolve imports from site-packages only (editable .pth
# paths have proven fragile across some deploy/cache paths).
RUN uv sync --frozen --no-dev --all-packages --no-editable

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
