# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt

# ── Stage 2: RUNTIME ────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /deps /deps
COPY scraper/ scraper/
ENV PYTHONPATH=/deps
ENV PYTHONUNBUFFERED=1

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser
USER appuser

CMD ["python", "-m", "scraper.main"]
