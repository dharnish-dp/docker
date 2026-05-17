# Lesson 04 — Your First Dockerfile

## Goal
Build your own Docker image from scratch using a Dockerfile.
Understand what each instruction does and how it becomes a layer.

---

## What is a Dockerfile?

A Dockerfile is a plain text recipe that tells Docker how to build your image,
step by step. Each instruction creates one layer in the final image.

---

## Dockerfile Instructions

```dockerfile
FROM   <base image>      # start from an existing image
WORKDIR <path>           # set working directory inside the image
COPY   <src> <dest>      # copy files from your machine into the image
RUN    <command>         # execute a shell command during build
ENV    KEY=VALUE         # set environment variables
EXPOSE <port>            # document which port the app listens on
CMD    ["executable"]    # default command when container starts
```

---

## The Dockerfile We Built

```dockerfile
FROM python:3.11-slim
```
Start from the official Python 3.11 slim image (Debian + Python pre-installed).
You inherit all its layers — ~182MB of OS and Python runtime — for free.

```dockerfile
WORKDIR /app
```
Creates `/app` inside the image and sets it as the working directory.
All subsequent COPY and RUN commands run from `/app`.
Equivalent to `mkdir /app && cd /app` baked into the image.

```dockerfile
COPY requirements.txt .
```
Copies `requirements.txt` from your Mac into `/app/` inside the image.
The `.` = current WORKDIR = `/app`.

```dockerfile
RUN pip install -r requirements.txt
```
Executes pip install **during build** — not at runtime.
The installed packages are baked into this layer permanently.
This is the heaviest layer — 18MB for the requests library.

```dockerfile
COPY app.py .
```
Copies the Python script into `/app/app.py`.

```dockerfile
CMD ["python", "app.py"]
```
The default command when the container starts.
Always use JSON array format `["python", "app.py"]` — not `CMD python app.py`.
(Reason explained in Lesson 05 — shell form vs exec form.)

---

## The app.py Script

```python
import requests
import sys

url = "https://httpbin.org/get"
response = requests.get(url)

print(f"Status code: {response.status_code}")
print(f"Python version inside container: {sys.version}")
print(f"Response JSON: {response.json()['url']}")
```

---

## Build Command

```bash
docker build -t my-first-image:1.0 .
```

- `-t my-first-image:1.0` — tag the image with name and version
- `.` — use the Dockerfile in the current directory
- Each Dockerfile step appears in the build output as `[1/5]`, `[2/5]`, etc.

---

## Layer Cache Behaviour

```
[1/5] FROM python:3.11-slim     → 0.0s  (cached — already on machine)
[2/5] WORKDIR /app              → 0.0s
[3/5] COPY requirements.txt .   → 0.0s
[4/5] RUN pip install           → 1.8s  (actual work)
[5/5] COPY app.py .             → 0.0s
```

If the image was already pulled, `FROM` is instant — Docker reuses cached layers.
Only steps that changed (or depend on changed steps) re-execute.
This is covered in depth in Lesson 05.

---

## Inspecting Layers

```bash
docker history my-first-image:1.0
```

Output (bottom = oldest, top = newest):

```
109MB   debian base OS              ← from python:3.11-slim (not you)
51.7MB  Python 3.11 compiled        ← from python:3.11-slim (not you)
──────────────────────────────────── your layers start here
8KB     WORKDIR /app                ← you
12KB    COPY requirements.txt       ← you
18MB    RUN pip install requests    ← you (requests library)
12KB    COPY app.py                 ← you
0B      CMD ["python" "app.py"]     ← you (metadata only, no size)
```

`CMD` costs 0 bytes — it's pure metadata, not a filesystem change.

---

## Key Commands

```bash
docker build -t <name>:<tag> .     # build image from Dockerfile in current dir
docker build --no-cache .          # build without using any cached layers
docker history <image>             # show all layers and their sizes
docker run <image>                 # run the container using CMD
```

---

## Check Your Understanding — Q&A

### Q1. What is the difference between `RUN` and `CMD`?

**Answer:**
- `RUN` executes at **image build time** — result is baked into a layer
- `CMD` executes at **container start time** — not during build at all

**Rule:** Everything that prepares the environment = `RUN`.
The command that starts your app = `CMD`.

**Common mistake:** Saying "RUN works during container creation." Wrong —
container creation and image build are two different moments. RUN = build time.

---

### Q2. Why does `CMD` cost 0 bytes in `docker history`?

**Answer:** `CMD` doesn't touch the filesystem. It only writes metadata into
the image — "when this container starts, run this command." No files created,
no packages installed, nothing written to disk. Zero bytes.

---

### Q3. You change `app.py` and rebuild. Which steps re-execute?

```dockerfile
FROM python:3.11-slim        # cached ✅ (unchanged)
WORKDIR /app                 # cached ✅ (unchanged)
COPY requirements.txt .      # cached ✅ (file unchanged)
RUN pip install              # cached ✅ (requirements unchanged)
COPY app.py .                # RE-RUNS ❌ (file changed → cache busted)
CMD ["python", "app.py"]     # RE-RUNS ❌ (comes after busted step)
```

**Golden rule of layer caching:**
> Once a layer's cache is busted, ALL layers after it re-run — no exceptions.

This is why instruction ORDER matters. Put the least-changing steps first,
most-changing steps last. See Lesson 05 for the full deep dive.

---

### Q4. What does `WORKDIR /app` do vs `RUN mkdir /app && cd /app`?

**Answer:** `WORKDIR /app` creates the directory AND sets it as the working
directory for all subsequent instructions. `RUN mkdir && cd` would only
work within that single RUN step — the next instruction would still be at `/`.

`WORKDIR` is persistent across all following instructions. It's also the
officially recommended approach — cleaner and more readable.
