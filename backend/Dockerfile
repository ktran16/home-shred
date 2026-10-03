# syntax=docker/dockerfile:1

# --- Stage 1: builder — resolve deps into a venv with uv (SPEC §14.2) ---
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 2: runtime ---
FROM python:3.12-slim AS runtime

# curl for the compose healthcheck; libgomp1 is required by onnxruntime (Piper TTS).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Pre-create the media mount point owned by appuser: a fresh named volume copies this
# ownership, otherwise Docker creates it root-owned and photo/TTS writes fail.
RUN mkdir -p /app/media && chown appuser:appuser /app/media

USER appuser
EXPOSE 8000

# Apply migrations, then start the server (single worker is fine for solo use).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
