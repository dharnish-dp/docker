# Lesson 11 — BuildKit & Advanced Builds

## Goal
Reduce image sizes dramatically, speed up builds with persistent caching,
inject secrets safely at build time, and build for multiple platforms.

## Prerequisites
Lessons 04, 05 — Dockerfile and Layer Caching

## After This Lesson You Will Be Able To
- Write multi-stage Dockerfiles that separate build from runtime
- Use cache mounts to make pip installs near-instant after the first build
- Inject secrets at build time without baking them into any layer
- Build images for multiple CPU architectures with one command

---

## What is BuildKit

BuildKit is the modern Docker build engine — enabled by default since Docker 23.
You are already using it. The `[+] Building` output with `=>` arrows is BuildKit.

It adds 4 powerful features that the old builder couldn't do:

```
Feature 1 → Multi-stage builds      (smaller images)
Feature 2 → Cache mounts            (faster builds)
Feature 3 → Secret mounts           (safer secrets)
Feature 4 → Multi-platform builds   (one image, any CPU)
```

---

## Feature 1 — Multi-Stage Builds

### The Real-World Problem First

When you install packages for your Python app, pip downloads them from PyPI.
Those downloaded files go somewhere on disk. After installation, you don't
need them anymore — but they're still in your image, taking up space.

More importantly: to INSTALL some Python packages (especially ones with C code
like numpy, pandas, psycopg2), Linux needs build tools:
- `gcc` (C compiler)
- `build-essential`
- `libpq-dev`
- `python3-dev`

These tools are only needed during installation. Your running app NEVER uses
them. But without multi-stage builds, they end up in your final image anyway.

```
Without multi-stage:
  Image = Ubuntu + Python + gcc + build tools + packages + your code
        = 800MB+   ← ships to production with tools you never use

With multi-stage:
  Build stage  = Ubuntu + Python + gcc + build tools + packages  (used + discarded)
  Final image  = Ubuntu + Python + packages + your code
              = 200MB   ← only what you actually need
```

---

### The Construction Site Analogy

Think of building a house:

```
You need:   bricks, cement, scaffolding, cranes, worker tools
To LIVE in: the finished house — walls, roof, windows

You don't ship the scaffolding and cranes with the house.
You use them to BUILD the house, then leave them at the construction site.
```

Multi-stage builds work the same way:

```
Stage 1 (builder) = construction site
  → has all the tools needed to build (gcc, pip, build deps)
  → installs packages
  → then gets DISCARDED — never goes to production

Stage 2 (runtime) = the finished house
  → starts completely fresh
  → takes ONLY the installed packages from Stage 1
  → nothing else carries over — no build tools, no compilers
```

---

### How It Looks in a Dockerfile

A Dockerfile with multi-stage has TWO `FROM` instructions.
Each `FROM` = a fresh start, a new stage.

```dockerfile
# ════════════════════════════════════════════
# STAGE 1: BUILDER  (the construction site)
# ════════════════════════════════════════════
FROM python:3.11 AS builder
#                  ↑
#                  "AS builder" gives this stage a name
#                  so Stage 2 can reference it

WORKDIR /app

COPY requirements.txt .

RUN pip install --target=/deps -r requirements.txt
#               ↑
#               --target=/deps = install packages into /deps folder
#               NOT into Python's system folder
#               This makes them easy to copy later


# ════════════════════════════════════════════
# STAGE 2: RUNTIME  (the finished house)
# ════════════════════════════════════════════
FROM python:3.11-slim
#    ↑
#    Fresh start — nothing from Stage 1 carries over automatically

WORKDIR /app

COPY --from=builder /deps /deps
#         ↑
#         --from=builder = copy FROM Stage 1 (not from your Mac)
#         /deps = the folder where we installed packages in Stage 1
#         /deps = paste them here in Stage 2

COPY app.py .

ENV PYTHONPATH=/deps
#   ↑
#   Tell Python: "look in /deps for packages"
#   Needed because packages are NOT in the default Python path

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["python", "app.py"]
```

---

### What Each New Instruction Means

#### `FROM python:3.11 AS builder`

```
FROM python:3.11   → use the FULL Python image (not slim)
                     Full image has gcc and all build tools
AS builder         → name this stage "builder"
                     Without a name, you can't reference it later
```

#### `pip install --target=/deps`

```
Without --target:
  pip installs into /usr/local/lib/python3.11/site-packages/
  This is buried inside Python — hard to copy selectively

With --target=/deps:
  pip installs into /deps/
  This is a clean folder with ONLY your packages
  Easy to copy: COPY --from=builder /deps /deps
```

#### `FROM python:3.11-slim` (Stage 2)

```
This is a completely fresh container.
Nothing from Stage 1 is here.
No gcc. No build tools. No pip cache. Nothing.
It's like starting with a brand new empty machine.
```

#### `COPY --from=builder /deps /deps`

```
COPY               → copy files (like always)
--from=builder     → but the SOURCE is Stage 1, not your Mac
                     "builder" matches the AS name in Stage 1
/deps              → source: the folder in Stage 1 where packages live
/deps              → destination: where to put them in Stage 2
```

#### `ENV PYTHONPATH=/deps`

```
Python normally looks for packages in:
  /usr/local/lib/python3.11/site-packages/

But our packages are in /deps/ (non-standard location).
PYTHONPATH tells Python: "also look here for packages"

Without this line: import requests → ModuleNotFoundError
With this line:    import requests → works ✅
```

---

### Visual: What Happens During `docker build`

```
docker build runs:

STAGE 1 (builder)
──────────────────────────────────────────────
  FROM python:3.11           ← full image, has gcc
  WORKDIR /app               ← create /app
  COPY requirements.txt      ← copy from Mac
  RUN pip install --target=/deps
    → downloads requests from PyPI
    → installs into /deps/
    → /deps/ now has: requests/, certifi/, urllib3/ etc.

  [Stage 1 complete — kept in memory during build]


STAGE 2 (runtime)
──────────────────────────────────────────────
  FROM python:3.11-slim      ← fresh, minimal image
  WORKDIR /app               ← create /app
  COPY --from=builder /deps /deps
    → copies /deps/ from Stage 1 into this stage
    → requests, certifi, urllib3 are now here
    → gcc, build tools are NOT here (were never in /deps)
  COPY app.py .              ← copy from Mac
  ENV PYTHONPATH=/deps       ← tell Python where packages are
  RUN adduser...             ← create non-root user
  USER appuser
  CMD ["python", "app.py"]

  [Stage 1 DISCARDED — garbage collected]
  [Final image = Stage 2 only]
```

---

### When Multi-Stage Makes the Biggest Difference

| App type | Build needs | Without | With |
|---|---|---|---|
| numpy, pandas, psycopg2 | gcc, build-essential | +300MB | Saved entirely |
| Go or Rust app | Full compiler toolchain | 500MB-1GB | ~10MB binary only |
| Node.js app | All devDependencies | 800MB | 100MB prod only |
| Pure Python (requests only) | Nothing special | ~200MB | ~200MB (small gain) |

---

## Feature 2 — Build Cache Mounts

### The Problem

Every time you change `requirements.txt`, pip re-downloads ALL packages
from the internet — even packages that didn't change.

If you have 30 packages and change one, pip downloads all 30 again.
On a slow connection: 2-3 minutes. In CI with 50 builds per day: hours wasted.

### What pip's Cache Is

When pip downloads a package, it keeps a copy in a local cache folder
(`/root/.cache/pip`). Next time you install the same package, pip reads
from this local cache instead of downloading again.

The problem: Docker destroys this cache folder after every `RUN` step
(because each layer is isolated). So the cache is useless.

### What a Cache Mount Does

A cache mount tells BuildKit: **"keep this folder between builds permanently"**.

```dockerfile
# Without cache mount — cache destroyed after each build
RUN pip install --target=/deps -r requirements.txt

# With cache mount — cache persists between builds forever
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt
```

```
--mount=type=cache          → "keep this folder between builds"
target=/root/.cache/pip     → "specifically this folder — pip's cache"
```

### What Actually Happens

```
Build 1 (first time):
  pip install runs
  Downloads requests from PyPI → saves to /root/.cache/pip
  Installs from cache into /deps
  Build time: 1.9 seconds

Build 2 (requirements changed — added flask):
  pip install runs again
  requests: found in /root/.cache/pip → installs instantly, no download
  flask: not in cache → downloads from PyPI → saves to cache
  Build time: 0.3 seconds (only flask downloaded)

Build 3 (only app.py changed — requirements unchanged):
  RUN pip install is CACHED (layer cache hit)
  pip install doesn't even run
  Build time: 0.0 seconds
```

### Cache Mount vs Layer Cache — The Key Difference

This confuses everyone. Here's the exact difference:

```
Layer cache (from Lesson 05):
  If the RUN instruction's inputs haven't changed → skip the RUN entirely
  docker build --no-cache → CLEARS this cache

BuildKit cache mount:
  The RUN instruction still runs
  But the folder /root/.cache/pip is preserved between runs
  pip finds packages there and skips downloading
  docker build --no-cache → does NOT clear cache mounts
```

In simple terms:
- Layer cache = "skip this step entirely"
- Cache mount = "run this step, but use saved files to speed it up"

### Live Proof from Our Session

```
Build 1 with --no-cache:   pip install = 1.9s  (downloaded from PyPI)
Build 2 normal:            pip install = 0.0s  (CACHED layer — skipped entirely)
Build 3 after req change:  pip install = 0.3s  (ran but used cache mount)
```

---

## Feature 3 — Secret Mounts at Build Time

### The Problem

Sometimes you need a password or token during `docker build` — for example:
- Downloading from a private PyPI server
- Cloning a private GitHub repo
- Accessing a licensed artifact

The instinct is to use `ARG`:

```dockerfile
ARG GITHUB_TOKEN
RUN git clone https://$GITHUB_TOKEN@github.com/private/repo
```

**This is dangerous.** The token gets baked into the image layer forever.

```bash
docker history myimage
# RUN git clone https://ghp_abc123token@github.com/...
#                          ↑
#                          Token fully visible to anyone who pulls your image
```

Even if you delete the file in a later layer, the layer with the token
still exists in the image history — anyone with `docker history` can see it.

### How Secret Mounts Work

```
Step 1: You create a file on your Mac with the secret value
Step 2: You pass it to docker build with --secret
Step 3: Inside the Dockerfile, you use --mount=type=secret to access it
Step 4: The secret is available ONLY during that ONE RUN step
Step 5: After the RUN step completes, the secret is completely gone
        It is NEVER written to any layer
        It is NOT in docker history
        It is NOT in the final image
```

### The Code

```bash
# Step 1 — create a file with the secret on your Mac
echo "ghp_myPrivateToken123" > /tmp/github_token.txt

# Step 2 — pass it to the build
docker build --secret id=github_token,src=/tmp/github_token.txt -t myimage .
#                     ↑              ↑
#                     name           where the file lives on your Mac
```

```dockerfile
# Step 3 — use it in a RUN step
RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN=$(cat /run/secrets/github_token) \
    git clone https://$GITHUB_TOKEN@github.com/private/repo
#   ↑
#   /run/secrets/github_token = where the secret file appears during THIS step
#   id=github_token must match --secret id= value
```

### The Secret's Lifecycle

```
Before the RUN step:   /run/secrets/github_token does NOT exist
During the RUN step:   /run/secrets/github_token exists, contains the token
After the RUN step:    /run/secrets/github_token does NOT exist

In the image layer:    token is NEVER written — not visible in docker history
In the final image:    token does NOT exist
```

### Verify It's Not in the Image

```bash
# Try to read the secret from a running container — it's gone
docker run --rm myimage cat /run/secrets/github_token
# cat: /run/secrets/github_token: No such file or directory ✅

# Check docker history — no token value visible
docker history myimage
# All you see is the command structure, not the secret value ✅
```

---

## Feature 4 — Multi-Platform Builds

### The Problem

Your Mac uses Apple Silicon (ARM64 chip).
Most production Linux servers use Intel/AMD (AMD64/x86_64 chip).

These are different CPU architectures. A Docker image built on your Mac
(ARM64) might not run on your production server (AMD64) — or runs in slow
emulation mode.

### What CPU Architecture Means for Docker

```
Your Mac (M1/M2/M3):      ARM64 architecture
Most Linux servers:        AMD64 (also called x86_64) architecture
AWS Graviton servers:      ARM64 (cheaper, more efficient)
Raspberry Pi 4:            ARM64

An ARM64 image running on AMD64:  works but slowly (emulated)
An AMD64 image running on ARM64:  works but slowly (emulated)
A native image:                   runs at full speed
```

### The Solution — Build for Both at Once

`docker buildx build --platform` builds your image for multiple
CPU architectures simultaneously and packages them as one tag.

```bash
# Step 1 — create a builder that supports multiple platforms
docker buildx create --use --name mybuilder
#                    ↑
#                    --use = make this the active builder immediately

# Step 2 — build for AMD64 and ARM64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t yourusername/myapp:1.0 \
  --push \
  .
# ↑
# --push is REQUIRED — multi-platform images can't be stored locally
# They must go to a registry (Docker Hub, GHCR, ECR)
```

### What the Result Looks Like

```
Docker Hub: yourusername/myapp:1.0
                │
                ├── AMD64 variant  ← 200MB image for Intel/AMD servers
                └── ARM64 variant  ← 200MB image for Apple/Graviton

When someone runs:
  docker pull yourusername/myapp:1.0

  On a Mac (ARM64)      → automatically pulls ARM64 variant
  On a Linux server     → automatically pulls AMD64 variant
  On AWS Graviton       → automatically pulls ARM64 variant

Same tag. Docker picks the right one automatically.
```

### When You Need This

- You deploy to Linux servers (AMD64) from a Mac (ARM64)
- Your team has a mix of Mac and Linux machines
- You want to publish a public image that works for everyone
- You deploy to AWS Graviton (ARM64 = cheaper instances)

---

## Practical — Build Your Own Multi-Stage Image

Let's build your `my-first-image` with all BuildKit features.

### Step 1 — Check your current image size

```bash
cd ~/Desktop/docker/my-first-image
docker images my-first-image
```

Note the current size. We'll compare after.

### Step 2 — View the Dockerfile with multi-stage

```bash
cat Dockerfile
```

Your Dockerfile already uses multi-stage (we built it in this lesson).
Stage 1 = full Python + pip install. Stage 2 = slim Python + packages only.

### Step 3 — Build with cache mount

```bash
docker build --no-cache -t my-first-image:3.0 .
# Watch the build output — note pip install time
```

### Step 4 — Build again — watch cache mount work

```bash
docker build --no-cache -t my-first-image:3.0 .
# pip install should be significantly faster — served from cache mount
```

### Step 5 — Compare sizes

```bash
docker images my-first-image
# Compare 1.0 (original) vs 3.0 (multi-stage)
```

### Step 6 — Inspect the builder stage directly

```bash
# Build only the builder stage (not the final runtime)
docker build --target builder -t debug-stage .

# Open a shell inside Stage 1 to see what's there
docker run --rm -it debug-stage sh

# Inside:
ls /deps         # packages are here
ls /usr/bin/gcc  # gcc is here — build tools in stage 1
exit

# Now check the runtime stage — gcc should be gone
docker run --rm -it my-first-image:3.0 sh -c "ls /usr/bin/gcc 2>&1 || echo 'gcc not found'"
# gcc not found ✅ — build tools didn't make it into Stage 2
```

---

## The Final Production Dockerfile (All Features Combined)

```dockerfile
# ════════════════════════════════════════════════════════
# STAGE 1: BUILDER
# Purpose: install packages in a full environment
# Discarded after build — never ships to production
# ════════════════════════════════════════════════════════
FROM python:3.11 AS builder

WORKDIR /app
COPY requirements.txt .

# Cache mount: pip's download cache persists between builds
# --target=/deps: install packages into /deps (easy to copy later)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --target=/deps -r requirements.txt


# ════════════════════════════════════════════════════════
# STAGE 2: RUNTIME
# Purpose: run the app with minimum footprint
# This is the final image that ships to production
# ════════════════════════════════════════════════════════
FROM python:3.11-slim

LABEL version="1.0" maintainer="you@example.com"

WORKDIR /app

# Copy ONLY the installed packages from Stage 1
# Everything else (gcc, build tools, pip cache) stays in Stage 1
COPY --from=builder /deps /deps

# Copy your application code
COPY app.py .

# Tell Python where to find the packages we copied
ENV PYTHONPATH=/deps

# Security: non-root user
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Health check (for use with docker compose condition: service_healthy)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Exec form: Python is PID 1, receives SIGTERM correctly on docker stop
CMD ["python", "app.py"]
```

---

## Command Reference — Every Command Explained

---

### `FROM python:3.11 AS builder`

```
FROM python:3.11   → use the full Python image (has gcc, build tools)
AS builder         → name this stage "builder"
                    This name is used in:
                    - COPY --from=builder (to copy from this stage)
                    - docker build --target builder (to build only this stage)
```

---

### `RUN --mount=type=cache,target=/root/.cache/pip pip install ...`

```
RUN                          → execute during build
--mount=type=cache           → attach a persistent cache volume to this step
target=/root/.cache/pip      → mount point = pip's download cache folder
                               pip reads from here before downloading from PyPI
                               pip writes to here after downloading
                               This folder persists between all future builds
                               This folder is NOT in the final image
pip install                  → runs normally, but uses cache when possible
```

---

### `pip install --target=/deps -r requirements.txt`

```
pip install          → install packages
--target=/deps       → install into /deps/ instead of Python's default location
                       Why: makes packages easy to copy with COPY --from=builder /deps /deps
                       Without --target: packages buried in Python internals, hard to isolate
-r requirements.txt  → read package list from file
```

---

### `COPY --from=builder /deps /deps`

```
COPY               → copy files
--from=builder     → source = Stage 1 (named "builder"), NOT your Mac
                     If you omit --from, source defaults to your Mac
/deps              → source path inside Stage 1
/deps              → destination path in Stage 2 (current stage)
```

---

### `ENV PYTHONPATH=/deps`

```
PYTHONPATH         → Python environment variable: where to look for packages
/deps              → the folder where we put packages with --target=/deps

Without this: Python only looks in /usr/local/lib/python3.11/site-packages/
              import requests → ModuleNotFoundError

With this:    Python also looks in /deps/
              import requests → found ✅
```

---

### `docker build --target builder -t debug-stage .`

```
--target builder   → stop at Stage 1 named "builder", don't run Stage 2
                     Builds only the first stage
                     Useful for debugging what's inside the build environment
-t debug-stage     → tag this partial build so you can run it
```

---

### `docker build --secret id=token,src=/tmp/token.txt -t myimage .`

```
--secret           → pass a secret to the build safely (BuildKit feature)
id=token           → name to use inside Dockerfile (referenced as id=token)
src=/tmp/token.txt → file on your Mac that contains the secret value
                     The FILE CONTENTS are injected — not the filename
-t myimage         → tag the result
```

---

### `RUN --mount=type=secret,id=token`

```
--mount=type=secret → inject the secret during this RUN step only
id=token            → which secret (must match --secret id= value)
                      Available at /run/secrets/token during this step
                      GONE after this step — not in any layer
```

---

### `docker buildx create --use --name mybuilder`

```
docker buildx      → extended build command supporting multi-platform
create             → create a new BuildKit builder instance
--use              → immediately switch to this builder (make it active)
--name mybuilder   → give it a name for future reference
```

---

### `docker buildx build --platform linux/amd64,linux/arm64 -t app:1.0 --push .`

```
docker buildx build         → build using the active buildx builder
--platform linux/amd64      → build for Intel/AMD 64-bit servers
           linux/arm64      → also build for ARM 64-bit (Mac M1/M2, Graviton)
-t app:1.0                  → tag the result (a manifest list pointing to both)
--push                      → push to registry (required — can't store locally)
.                           → build context
```

---

## Check Your Understanding — Q&A

### Q1. You have a Dockerfile with two FROM instructions. How many images does `docker build` produce?

**Answer:** ONE image — the final stage only. Stage 1 (builder) is a temporary
intermediate that Docker uses during the build and then discards. Only the last
stage (or the `--target` stage) becomes the final image. Stage 1 never appears
in `docker images`.

---

### Q2. What is the difference between `--no-cache` and a cache mount?

**Answer:**
- `--no-cache` skips the **layer cache** — Docker re-executes every instruction
  instead of reusing cached layers. The `RUN pip install` step runs again.
- A **cache mount** (`--mount=type=cache`) persists pip's download folder between
  builds. Even with `--no-cache`, pip finds its downloaded packages in the cache
  mount and installs from there — no network download needed.

`--no-cache` = ignore layer cache (force re-run steps)
cache mount = speed up the step when it runs (avoid re-downloading)
Both can be true at the same time.

---

### Q3. Why can't you access a secret mount after the RUN step that used it?

**Answer:** Secret mounts are never written to any filesystem layer. They exist
only in memory during the single `RUN` step. When the step finishes, the memory
is cleared. There is no file left in the image, no entry in `docker history`,
and no way to recover the value. This is by design — it's what makes secret
mounts safe.

---

### Q4. Your build stage uses `python:3.11` (full, ~1GB). Runtime uses `python:3.11-slim` (~200MB). What is the final image size?

**Answer:** ~200MB — the final image is based entirely on `python:3.11-slim`.
The `python:3.11` build stage is completely discarded after the build.
Only what you explicitly `COPY --from=builder` makes it into the final image.
The 1GB of build tools never ships to production.

---

### Q5. What does `PYTHONPATH=/deps` do and why is it needed?

**Answer:** When you install packages with `pip install --target=/deps`, they go
into `/deps/` instead of Python's standard `site-packages` folder. Python doesn't
look in `/deps` by default — it only looks in `site-packages`. `PYTHONPATH=/deps`
tells Python "also search this folder for importable packages." Without it, every
`import requests` would fail with `ModuleNotFoundError` even though the package
is physically present in `/deps/`.
