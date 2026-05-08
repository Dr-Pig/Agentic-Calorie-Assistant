FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by psycopg2-binary and local governance checks.
RUN apt-get update && \
    apt-get install -y --no-install-recommends git libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS dev

# Dev/test target keeps repo verification inputs available for Docker Compose.
COPY . .

RUN mkdir -p runtime/db runtime/artifacts/session_records

CMD ["python", "scripts/verify_environment.py"]
