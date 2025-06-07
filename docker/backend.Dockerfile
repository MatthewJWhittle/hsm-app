FROM python:3.11-slim



# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the UV binary from the official UV image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR /app

# Install Python dependencies
COPY pyproject.toml /app/pyproject.toml

RUN uv sync && \
    uv pip install uvicorn

# Copy application code
COPY . /app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"] 