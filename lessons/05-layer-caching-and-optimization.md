# Lesson 05 — Layer Caching & Build Optimization

## Goal
Write Dockerfiles that build in seconds, not minutes. Understand why
instruction order is the single biggest lever for build performance.

---

## The Golden Rule

> **Once a layer's cache is busted, ALL layers after it re-run. No exceptions.**

---

## The Core Principle

Order instructions from least likely to change → most likely to change.

```
LEAST LIKELY TO CHANGE    → top of Dockerfile
MOST LIKELY TO CHANGE     → bottom of Dockerfile
```

| Instruction | How often it changes |
|---|---|
| `FROM python:3.11-slim` | Once a year (Python version bump) |
| `RUN apt-get install` | Rarely (new system dependency) |
| `COPY requirements.txt` + `RUN pip install` | When you add a package |
| `COPY app.py` | Every time you touch your code |

---

## Bad Dockerfile vs Good Dockerfile

### BAD — `COPY . .` before `pip install`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .                           # copies EVERYTHING including app.py
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

**What happens when you change one line in `app.py`:**
```
WORKDIR /app          → CACHED ✅
COPY . .              → BUSTED ❌  (app.py changed)
RUN pip install       → RE-RUNS ❌  (wastes 60-90s every code change)
CMD                   → RE-RUNS ❌
```

`pip install` runs on **every code change** — even if requirements.txt
didn't change at all.

---

### GOOD — Split COPY so requirements come first

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .            # copy ONLY requirements first
RUN pip install -r requirements.txt
COPY app.py .                      # copy code AFTER pip install
CMD ["python", "app.py"]
```

**What happens when you change `app.py`:**
```
WORKDIR /app          → CACHED ✅
COPY requirements.txt → CACHED ✅  (didn't change)
RUN pip install       → CACHED ✅  (skipped entirely)
COPY app.py           → RE-RUNS ❌  (changed — but last real step)
CMD                   → RE-RUNS ❌  (0 bytes, instant)
```

`pip install` only re-runs when `requirements.txt` changes.

---

## Live Proof — Build Time Comparison

| Scenario | Bad Dockerfile | Good Dockerfile |
|---|---|---|
| First build | 2.8s | 2.4s |
| After changing `app.py` | 2.1s (pip re-ran) | 0.1s (pip cached) |

On a real project with 50 dependencies:
- Bad: 60-90s per build
- Good: 1-2s per build

---

## The `.dockerignore` File

When you run `docker build`, Docker sends your entire project folder to the
build engine before reading the Dockerfile. This is called the **build context**.

`.dockerignore` works exactly like `.gitignore` — excludes files from the
build context.

```
# .dockerignore
.git            ← git history, can be hundreds of MBs
__pycache__     ← Python bytecode, regenerated inside container
*.pyc / *.pyo   ← compiled Python files
.env            ← CRITICAL: contains secrets, NEVER copy into image
.venv / venv/   ← local virtualenv, image has its own Python
*.log           ← log files, irrelevant to build
.DS_Store       ← Mac metadata
```

**The `.env` entry is the most critical.** Secrets baked into image layers
are permanently exposed if the image is ever pushed to a registry — even if
you later delete the file in a subsequent layer.

### Build context size comparison

```
Without .dockerignore: transferring context: 376B
With .dockerignore:    transferring context: 63B
```

On a real project this difference is megabytes vs bytes — a large build
context slows every build before a single Dockerfile line runs.

---

## Summary — Optimization Checklist

1. **Split COPY** — copy `requirements.txt` separately, install, THEN copy code
2. **Order by change frequency** — least-changing instructions at the top
3. **Always have `.dockerignore`** — exclude `.git`, `venv`, `.env`, caches
4. **Never `COPY . .` before `RUN`** — it busts the cache on every code change

---

## Key Commands

```bash
docker build -t <name>:<tag> .          # build image
docker build --no-cache .               # build ignoring all cached layers
docker history <image>                  # see layers and sizes
```

---

## Check Your Understanding — Q&A

### Q1. You have 20 pip packages. You change one line in `app.py`. With the good Dockerfile, does pip install re-run?

**Answer:** No. `requirements.txt` didn't change, so the `COPY requirements.txt`
layer is cached, which means `RUN pip install` is also cached.
`pip install` only re-runs when `requirements.txt` itself changes.

---

### Q2. What is the build context and why does it matter?

**Answer:** The build context is everything in your project folder that Docker
sends to the build engine before processing the Dockerfile. A large build
context (big `.git` folder, test datasets, logs) slows every build.
`.dockerignore` trims it to only what's needed.

---

### Q3. Why is `.env` the most important entry in `.dockerignore`?

**Answer:** `.env` contains secrets (API keys, passwords, tokens). If it gets
copied into an image layer and that image is pushed to a registry, the secrets
are permanently exposed — even if you delete the file in a later layer, because
each layer is stored independently and the secret layer still exists.

---

### Q4. What is the single most impactful change you can make to a slow Dockerfile?

**Answer:** Move `COPY . .` to AFTER the dependency installation step.
Split it into: `COPY requirements.txt .` → `RUN pip install` → `COPY app.py .`
This ensures the expensive install step is cached on every code-only change.
