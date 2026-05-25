# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

# Cache mount — pip packages cached between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ── Stage 2: RUNTIME ────────────────────────────────────────────────
# Use the official Selenium standalone Chrome image as base
# It includes: Chrome browser + ChromeDriver + all required system libraries
FROM selenium/standalone-chrome:latest

# Switch to root to install Python
USER root

# Install Python 3.11
RUN apt-get update && apt-get install -y python3.11 python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

# Create symlink so "python" works
RUN ln -s /usr/bin/python3.11 /usr/bin/python

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /deps /deps

# Copy all test files
COPY tests/ tests/

# Create reports directory — test output saved here
RUN mkdir -p reports

ENV PYTHONPATH=/deps

# Non-root user (selenium image provides "seluser")
USER seluser

# Default command: run all tests and generate HTML report
CMD ["python", "-m", "pytest", "tests/", "-v", \
     "--html=reports/report.html", "--self-contained-html"]
