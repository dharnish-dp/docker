# Lesson 11 — BuildKit & Advanced Builds

## Goal
Reduce image sizes dramatically, speed up builds with persistent caching,
inject secrets safely at build time, and build for multiple platforms.

## Prerequisites
Lessons 04, 05 — Dockerfile and Layer Caching

## After This Lesson You Will Be Able To
- Write multi-stage Dockerfiles that separate build from runtime
- Use cache mounts to make pip/npm installs near-instant after the first build
- Inject secrets at build time without baking them into any layer
- Build images for multiple CPU architectures with one command

---

## What is BuildKit

BuildKit is the modern Docker build engine — enabled by default since Docker 23.

```
Old builder:                    BuildKit:
- Sequential stages             - Parallel independent stages
- No persistent cache           - Persistent cache mounts
- Secrets via ARG/ENV (unsafe)  - Secret mounts (never in layers)
- One platform per build        - Multi-platform in one command
```

You are already using BuildKit. The `[+] Building` output with `=>` arrows
is BuildKit syntax.

---

## Feature 1 — Multi-Stage Builds

### The Problem

To build a Python app you need compilers and build tools.
To run it you only need the installed packages and your code.
Why ship build tools to production?

```
Without multi-stage:
  Final image = base OS + Python + build tools + packages + code = 800MB+

With multi-stage:
  Build stage  = base OS + Python + build tools + packages  (discarded)
  Final image  = base OS + Python + packages + code         = 200MB
```

### How It Works

Multiple `FROM` instructions — each starts a fresh stage.
Copy only what you need from the build stage into the final stage.

```dockerfile
# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11 AS builder

WORKDIR /app
COPY requirements.txt .

# Install packages into /deps (not system Python)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ── Stage 2: RUNTIME ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy ONLY the installed packages from builder — no build tools follow
COPY --from=builder /deps /deps

COPY app.py .

ENV PYTHONPATH=/deps

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["python", "app.py"]
```

### Key Instructions Explained

```dockerfile
FROM python:3.11 AS builder
```
- `AS builder` = name this stage "builder" so other stages can reference it
- Use the full image here — it has all build tools

```dockerfile
pip install --target=/deps
```
- `--target=/deps` = install packages into `/deps` folder instead of system Python
- This makes it easy to copy just the packages: `COPY --from=builder /deps /deps`

```dockerfile
FROM python:3.11-slim
```
- Fresh start — nothing from the builder stage carries over unless explicitly copied
- Use `slim` here — minimal runtime, no build tools

```dockerfile
COPY --from=builder /deps /deps
```
- `--from=builder` = copy from the named stage, not from your Mac
- Copies only the installed packages — leaves behind gcc, pip cache, build tools

```dockerfile
ENV PYTHONPATH=/deps
```
- Tells Python to look for packages in `/deps`
- Required because packages aren't in the default system Python path

### When Multi-Stage Makes the Biggest Difference

| App type | Build stage needs | Without multi-stage | With multi-stage |
|---|---|---|---|
| C extensions (numpy, pandas) | gcc, build-essential | +300MB | Saved |
| Go / Rust app | Full compiler | 500MB-1GB | ~10MB binary |
| Node.js app | devDependencies | 800MB | 100MB |
| Simple Python (pure packages) | Nothing special | ~200MB | ~200MB (minimal gain) |

---

## Feature 2 — Build Cache Mounts

### The Problem

Every time `requirements.txt` changes, `pip install` re-downloads all packages
from PyPI — even packages that haven't changed.

### How Cache Mounts Work

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt
```

```
--mount=type=cache     → create a persistent BuildKit cache volume
target=/root/.cache/pip → mount it at pip's download cache directory
```

- First build: downloads normally (1.9s for requests)
- Every build after: serves from local cache (0.0s)
- Survives `docker build --no-cache` — cache mounts are outside layer cache
- Never baked into the image — the cache stays on your machine only

### Live Proof

```
Build 1 (--no-cache):   pip install = 1.9s  (downloaded from PyPI)
Build 2 (with cache):   pip install = 0.0s  (served from cache mount) ✅
```

### Cache Mount for Other Tools

```dockerfile
# npm (Node.js)
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Go modules
RUN --mount=type=cache,target=/go/pkg/mod \
    go build ./...

# apt-get
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get install -y curl wget
```

---

## Feature 3 — Secret Mounts at Build Time

### The Problem

You need a token during build (private PyPI, private git repo).
Using `ARG` or `ENV` bakes it into a layer — permanently exposed in
`docker history` and any registry the image is pushed to.

### How Secret Mounts Work

```bash
# Step 1 — create secret file on Mac
echo "my-private-token" > /tmp/pip_token.txt

# Step 2 — pass it to the build
docker build --secret id=pip_token,src=/tmp/pip_token.txt -t myimage .
```

```dockerfile
# Step 3 — use it in a RUN step ONLY
RUN --mount=type=secret,id=pip_token \
    PIP_TOKEN=$(cat /run/secrets/pip_token) \
    pip install --index-url https://user:$PIP_TOKEN@private.pypi.example.com/simple/ \
    --target=/deps -r requirements.txt
```

```
--mount=type=secret,id=pip_token  → inject secret at /run/secrets/pip_token
                                    available ONLY during this RUN step
                                    completely gone after — not in any layer
```

### Verify the Secret Is Not in the Image

```bash
docker run --rm myimage cat /run/secrets/pip_token
# cat: /run/secrets/pip_token: No such file or directory ✅

docker history myimage
# No trace of the token value in any layer ✅
```

Compare to the dangerous way:
```dockerfile
ARG PIP_TOKEN              # WRONG — visible in docker history forever
RUN pip install ... $PIP_TOKEN
```

---

## Feature 4 — Multi-Platform Builds

Your Mac runs ARM64. Your production server runs AMD64. By default
`docker build` builds for your current CPU architecture only.

`docker buildx` builds for multiple platforms simultaneously:

```bash
# Enable buildx (already in Docker Desktop)
docker buildx create --use --name mybuilder

# Build for both ARM64 and AMD64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:1.0 \
  --push \          # must push to registry — can't load multi-platform locally
  .
```

The result is a **manifest list** — one image tag that automatically
serves the right architecture to whoever pulls it:

```
docker pull myapp:1.0 on Mac (ARM64)     → pulls ARM64 variant automatically
docker pull myapp:1.0 on Linux (AMD64)   → pulls AMD64 variant automatically
Same tag. No configuration needed.
```

### When You Need Multi-Platform

- Your team has mixed Mac (ARM) and Linux (AMD) machines
- You deploy to AWS Graviton (ARM) instances — they're cheaper
- You publish public images to Docker Hub

---

## The Final Production Dockerfile

Combines everything from all 11 lessons:

```dockerfile
# ── Stage 1: BUILD ──────────────────────────────────────────────────
FROM python:3.11 AS builder

WORKDIR /app
COPY requirements.txt .

# Cache mount = pip never re-downloads unchanged packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ── Stage 2: RUNTIME ────────────────────────────────────────────────
FROM python:3.11-slim

# Metadata
LABEL version="1.0" maintainer="you@example.com"

WORKDIR /app

# Only runtime packages — no build tools in final image
COPY --from=builder /deps /deps
COPY app.py .

ENV PYTHONPATH=/deps

# Security: non-root user with correct ownership
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Health check — verify app is actually responding
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Exec form — PID 1 = Python, receives SIGTERM correctly
CMD ["python", "app.py"]
```

---

## Command Reference — Every Command Explained

---

### `docker build -t myapp:1.0 .`

```
docker build       → read Dockerfile, execute each instruction, produce an image
-t myapp:1.0       → tag the final image with name "myapp" and version "1.0"
                    Format: name:tag
                    If no tag given, defaults to "latest" (avoid in production)
.                  → build context — the folder Docker sends to the build engine
                    Dockerfile must exist in this folder (or specify with -f)
```

---

### `docker build --no-cache -t myapp:1.0 .`

```
--no-cache         → ignore ALL cached layers — re-execute every instruction
                    Use to simulate a clean first build
                    Does NOT clear BuildKit cache mounts — those are separate
                    Use when: testing full build time, troubleshooting stale cache
```

---

### `docker build --secret id=mytoken,src=/tmp/token.txt -t myapp:1.0 .`

```
--secret           → pass a secret to the build (BuildKit only)
id=mytoken         → the name of the secret inside the build (referenced in Dockerfile)
src=/tmp/token.txt → path to the secret file on your Mac
                    The file contents are injected, not the path itself
-t myapp:1.0       → tag the resulting image
```

In the Dockerfile, access via:
```dockerfile
RUN --mount=type=secret,id=mytoken \
    cat /run/secrets/mytoken
#              ↑
#              id= must match the --secret id= value
```

---

### `RUN --mount=type=cache,target=/root/.cache/pip`

```
RUN                → execute a shell command during build
--mount=type=cache → attach a BuildKit-managed persistent cache volume to this step
target=/root/.cache/pip  → where to mount the cache inside the container during build
                    /root/.cache/pip = pip's download cache directory
                    Packages downloaded here are reused in future builds
                    This directory is NOT included in the final image layer
```

The cache volume:
- Created automatically by BuildKit on first use
- Persists on your Mac between builds
- Survives `docker build --no-cache`
- Never baked into any image layer

---

### `pip install --target=/deps -r requirements.txt`

```
pip install        → install Python packages
--target=/deps     → install into /deps directory instead of system Python
                    Keeps packages separate from the Python interpreter
                    Allows easy COPY --from=builder /deps /deps in runtime stage
-r requirements.txt → read package list from requirements.txt
```

Without `--target`, packages go into Python's site-packages and are harder
to copy selectively into the runtime stage.

---

### `RUN --mount=type=secret,id=pip_token`

```
RUN                → execute command during build
--mount=type=secret → inject a secret from docker build --secret into this step
id=pip_token       → which secret to inject (must match --secret id=)
                    Mounted at: /run/secrets/pip_token (by default)
                    Custom path: --mount=type=secret,id=pip_token,dst=/my/path
```

Properties of secret mounts:
- Available ONLY during this single RUN step
- Never written to any image layer
- Not visible in `docker history`
- Not present in the final image at all

---

### `COPY --from=builder /deps /deps`

```
COPY               → copy files
--from=builder     → source is the "builder" stage, NOT your Mac filesystem
                    "builder" must match the AS name in a previous FROM instruction
                    e.g. FROM python:3.11 AS builder
/deps              → source path inside the builder stage
/deps              → destination path in the current stage
```

This is what makes multi-stage builds work — selectively copying only
what the runtime needs, leaving build tools behind.

---

### `ENV PYTHONPATH=/deps`

```
ENV                → set an environment variable in the image
PYTHONPATH=/deps   → tells Python to search /deps for importable packages
                    in addition to the default site-packages
                    Required when packages are installed with --target=/deps
                    rather than into the system Python path
```

---

### `docker buildx create --use --name mybuilder`

```
docker buildx      → Docker's extended build command (supports multi-platform)
create             → create a new builder instance
--use              → set this new builder as the active builder immediately
--name mybuilder   → give it a name so you can reference or remove it later
```

A builder instance is a BuildKit daemon. The default one only supports
your current platform. A new one supports multiple platforms via emulation.

---

### `docker buildx build --platform linux/amd64,linux/arm64 -t myapp:1.0 --push .`

```
docker buildx build → build using the active buildx builder
--platform          → target architectures to build for (comma-separated)
linux/amd64         → standard Intel/AMD 64-bit (most Linux servers)
linux/arm64         → ARM 64-bit (Apple Silicon, AWS Graviton, Raspberry Pi 4)
-t myapp:1.0        → tag for the manifest list (points to both arch variants)
--push              → push directly to a registry after building
                    Required: multi-platform images cannot be stored locally
.                   → build context
```

Other platforms you might need:
```
linux/386           → 32-bit Intel (very rare)
linux/arm/v7        → 32-bit ARM (Raspberry Pi 3)
windows/amd64       → Windows containers
```

---

### `docker build --target builder -t debug-build .`

```
docker build       → build an image
--target builder   → stop building at the "builder" stage — don't continue to runtime stage
                    Useful for debugging: inspect what's inside the build environment
-t debug-build     → tag this partial build so you can run it
.                  → build context
```

After this, run:
```bash
docker run --rm -it debug-build sh
# Opens an interactive shell inside the builder stage
# You can ls /deps, check pip version, verify installed packages
```

---

### `docker history myimage`

```
docker history     → show all layers in an image from newest (top) to oldest (bottom)
myimage            → the image to inspect
```

Output columns:
```
IMAGE       → layer ID (or <missing> for base image layers)
CREATED     → when this layer was created
CREATED BY  → the Dockerfile instruction that created it
SIZE        → disk space this layer adds to the image
COMMENT     → optional comment
```

Use to verify:
- A secret is NOT visible in any layer (after using --mount=type=secret)
- Layer sizes (find which instruction is bloating your image)
- What the base image contains (inherited layers)

---

## Check Your Understanding — Q&A

### Q1. What is the difference between `--no-cache` and a cache mount?

**Answer:** `--no-cache` clears the **layer cache** — Docker re-executes every
instruction instead of reusing cached layers. But BuildKit cache mounts are
stored separately from the layer cache. `pip install` with a cache mount
still runs (the RUN layer is not cached), but pip finds its downloaded packages
in the cache mount and installs from there instantly — no network download needed.

---

### Q2. Why must you use `--push` with multi-platform builds?

**Answer:** A multi-platform image is a manifest list — a pointer to multiple
image variants. Docker's local image store only supports one architecture at a
time (your current machine's). To store all variants together, they must be
pushed to a registry that supports manifest lists (Docker Hub, GHCR, ECR all do).

---

### Q3. A secret passed via `ARG` vs `--mount=type=secret` — what's the difference?

**Answer:** `ARG` bakes the value into the build layer — visible in
`docker history`, stored in the image metadata, and exposed to anyone who
pulls the image from a registry. `--mount=type=secret` injects the secret
only during that single `RUN` step in memory — it never touches any layer,
never appears in history, and is completely gone when the step finishes.

---

### Q4. Your build stage uses `python:3.11` (full, 1GB). Your runtime uses `python:3.11-slim` (200MB). What is the size of the final image?

**Answer:** ~200MB — the final image is based entirely on `python:3.11-slim`.
The `python:3.11` build stage is discarded after the build. Only what you
explicitly `COPY --from=builder` makes it into the final image.
The 1GB build image never ships to production.
