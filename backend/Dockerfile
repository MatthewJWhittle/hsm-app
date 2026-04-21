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

# Production / Cloud Run: run uvicorn from the venv created by `RUN uv sync` above.
# Do not use `uv run` here — by design it syncs/updates the project env before the command,
# which repeats workspace work on every cold start. See uv docs: "Using uv in Docker".
#
# Local dev: `docker-compose.yml` overrides CMD with `uv sync && uv run uvicorn … --reload` so a
# bind-mounted repo stays in sync and gets reload; that path is correct for development only.
CMD ["/app/.venv/bin/uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
