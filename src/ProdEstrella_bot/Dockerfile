# ══════════════════════════════════════════════════════════════════════════════
# ProdEstrella Bot — Multi-stage Dockerfile (Python 3.13)
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build dependencies ────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy only dependency files first (Docker cache layer optimization)
COPY pyproject.toml README.md ./

# Create minimal package marker so uv can resolve the project
RUN mkdir -p app && touch app/__init__.py

# Install dependencies into an isolated virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN uv pip install --no-cache .

# ── Stage 2: Runtime image ─────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Security hardening: run as non-root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

WORKDIR /app

# Copy application source
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup alembic.ini ./
COPY --chown=appuser:appgroup seed_db.py ./

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run with uvicorn — workers controlled by environment
CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--loop", "uvloop", \
    "--http", "httptools", \
    "--proxy-headers", \
    "--forwarded-allow-ips", "*"]
