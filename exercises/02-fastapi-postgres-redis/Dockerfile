# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11 AS builder

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ── Stage 2: RUNTIME ────────────────────────────────────────────────
FROM python:3.11-slim

LABEL version="1.0" maintainer="you@example.com"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /deps /deps

# Copy application code
COPY app/ app/

ENV PYTHONPATH=/deps
ENV PYTHONUNBUFFERED=1

# Security: non-root user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Health check: verify FastAPI is responding
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# uvicorn = production ASGI server for FastAPI
# --host 0.0.0.0 = listen on all interfaces (required inside container)
# --port 8000 = internal port
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
