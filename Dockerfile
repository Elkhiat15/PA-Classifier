# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# One image that contains BOTH the compiled React frontend and the FastAPI
# backend. The backend serves the frontend at "/" and the API under "/api",
# so the whole app runs on a single port (8000) with no CORS or proxy needed.
#
# API keys are NEVER baked in: they are read from the runtime environment
# (docker compose env_file / --env-file). See .dockerignore.
# ---------------------------------------------------------------------------

# ---- Stage 1: build the React frontend (Vite) ----
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime + served static assets ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PA_API_HOST=0.0.0.0 \
    PA_API_PORT=8000 \
    PA_STATIC_DIR=/app/static

# Poetry installs the backend into the system environment (no venv needed).
RUN pip install "poetry==2.1.1" && poetry config virtualenvs.create false

WORKDIR /app

# Install Python deps first (better layer caching). --no-root skips the
# project itself, so dependency layers survive source changes.
COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry install --only main --no-root

# Copy the backend package, then install it so the `pa-serve` console script
# (declared in [tool.poetry.scripts]) is created. Deps are already present, so
# this second install only wires up the project + entry point.
COPY backend/policy_classifier ./policy_classifier
RUN poetry install --only main

# Copy the compiled frontend where the app serves it from.
COPY --from=frontend /app/frontend/dist /app/static

EXPOSE 8000

# `pa-serve` is the Poetry script -> policy_classifier.server:main (uvicorn).
CMD ["pa-serve"]