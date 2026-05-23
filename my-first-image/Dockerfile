# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11 AS builder

WORKDIR /app

COPY requirements.txt .

# Install packages — cache mount keeps pip cache between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ── Stage 2: RUNTIME ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy ONLY the installed packages from the builder stage
COPY --from=builder /deps /deps

# Copy application code
COPY app.py .

# Tell Python where to find the packages
ENV PYTHONPATH=/deps

# Security: non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["python", "app.py"]
