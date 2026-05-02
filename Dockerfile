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

# Dev/test target keeps repo verification inputs available for Docker Compose and devcontainers.
COPY . .

RUN mkdir -p runtime/db runtime/artifacts/session_records

CMD ["python", "scripts/verify_environment.py"]

FROM base AS runtime

# Copy application code
COPY alembic/ alembic/
COPY alembic.ini .
COPY app/ app/
COPY static/ static/
COPY data_build/ data_build/
COPY .env.example .env.example

# Ensure runtime directories exist
RUN mkdir -p runtime/db runtime/artifacts/session_records

# Expose port (Render / Railway / Fly default)
EXPOSE 8000

# Run Alembic migrations then start uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
