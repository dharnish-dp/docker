# Lesson 02 — Core Building Blocks: Images, Containers, Registries

## Goal
Understand the three fundamental concepts of Docker and how they relate to
each other. Every Docker command you ever run connects back to one of these.

---

## The Three Building Blocks

```
REGISTRY (Docker Hub, GHCR, ECR)
    │
    │  docker pull / docker push
    ▼
IMAGE  (blueprint — read-only, like a class definition)
    │
    │  docker run
    ▼
CONTAINER  (running instance — like an object instantiated from a class)
```

---

## 1. Image

An image is a **read-only blueprint** for a container.

**Python analogy:** An image is like a Python *class definition*. It defines
what the container will look like — but it's not running anything yet.

An image contains:
- A base OS filesystem (e.g., Ubuntu, Alpine, Debian)
- Your application code
- Python + all dependencies
- Any config files, scripts, env vars baked in

An image is made of **layers** (we go deep on this in Lesson 04). Each
instruction in a Dockerfile creates one layer:

```
Layer 4: COPY app.py /app/          ← your code
Layer 3: RUN pip install selenium   ← your dependencies
Layer 2: RUN apt-get install python ← system packages
Layer 1: FROM ubuntu:22.04          ← base OS
```

Layers are stacked and cached. If Layer 2 hasn't changed, Docker reuses
the cached version instead of rebuilding it. This is why Docker builds are fast.

**Images are immutable.** You never modify an image — you build a new one.

---

## 2. Container

A container is a **running instance of an image**.

**Python analogy:** If an image is a class, a container is an object —
an instance of that class, running in memory.

```python
# Python
class MyApp:       # ← this is like an Image
    pass

app = MyApp()      # ← this is like a Container (running instance)
app2 = MyApp()     # ← you can run multiple containers from one image
```

Key properties:
- You can run **many containers from one image** simultaneously
- Each container is **isolated** — its own filesystem, network, processes
- Containers are **ephemeral by default** — when stopped, their changes
  are lost (unless you use volumes — Lesson 07)
- A container adds a thin **read-write layer** on top of the image layers

```
┌─────────────────────────────────┐
│  Container read-write layer     │  ← changes here are lost on stop
├─────────────────────────────────┤
│  Image Layer 4 (your code)      │  ← read-only
│  Image Layer 3 (pip packages)   │  ← read-only
│  Image Layer 2 (system tools)   │  ← read-only
│  Image Layer 1 (base OS)        │  ← read-only
└─────────────────────────────────┘
```

---

## 3. Registry

A registry is a **storage and distribution server for images**.

Think of it like PyPI — but for Docker images instead of Python packages.

| PyPI equivalent | Docker equivalent |
|---|---|
| PyPI (pypi.org) | Docker Hub (hub.docker.com) |
| `pip install requests` | `docker pull python:3.11` |
| `pip publish` | `docker push myimage:1.0` |
| Package name + version | Image name + tag |

**Docker Hub** is the default public registry. It hosts:
- Official images: `python`, `postgres`, `nginx`, `redis`, `ubuntu`
- Community images: `username/imagename`

Other registries:
- GHCR (GitHub Container Registry) — `ghcr.io/...`
- ECR (AWS Elastic Container Registry) — `123.dkr.ecr.us-east-1.amazonaws.com/...`
- GCR (Google Container Registry) — `gcr.io/...`
- Self-hosted (Harbor, Nexus)

---

## Image Naming Convention

```
registry/username/imagename:tag

Examples:
  python:3.11                     ← official image, no registry prefix = Docker Hub
  ubuntu:22.04                    ← official image
  nginx:latest                    ← official image, "latest" tag
  myusername/myapp:1.0            ← your image on Docker Hub
  ghcr.io/myorg/myapp:abc123      ← image on GitHub Container Registry
```

**Never use `latest` in production** — it's a moving target. Always pin to a
specific version tag so your builds are reproducible.

---

## Hands-On: Your First Docker Commands

Run these one at a time. Observe the output carefully.

### Step 1 — Pull an image from Docker Hub

```bash
docker pull python:3.11-slim
```

This downloads the official Python 3.11 image (slim variant = smaller size).
You'll see each layer download separately.

### Step 2 — List images on your machine

```bash
docker images
```

You'll see the image you just pulled with its size, tag, and image ID.

### Step 3 — Run a container from that image

```bash
docker run python:3.11-slim python --version
```

Breaking this down:
- `docker run` = create and start a container
- `python:3.11-slim` = use this image
- `python --version` = run this command inside the container

The container starts, runs `python --version`, prints the output, then exits.

### Step 4 — Run an interactive container

```bash
docker run -it python:3.11-slim bash
```

- `-i` = interactive (keep stdin open)
- `-t` = allocate a terminal (TTY)

You're now INSIDE the container. Try:
```bash
python --version
ls /
cat /etc/os-release
exit
```

Notice: this is a Linux filesystem, even though you're on a Mac. That's the
isolation in action.

### Step 5 — List running containers

```bash
docker ps
```

After exiting, this shows nothing (container stopped). Try:

```bash
docker ps -a
```

`-a` shows ALL containers including stopped ones.

### Step 6 — List images again and check the image ID

```bash
docker images
```

### Step 7 — Remove a stopped container

```bash
docker rm <container_id>
```

Get the container ID from `docker ps -a`. You only need the first few characters.

### Step 8 — Remove an image

```bash
docker rmi python:3.11-slim
```

You can only remove an image if no containers (even stopped) are using it.

---

## Live Observations (from hands-on session)

- `docker pull` downloads layers in parallel — each line in the output is one layer
- The image ID in `docker images` matches the first 12 chars of the digest from `docker pull`
- `CONTENT SIZE` (48MB) vs `DISK USAGE` (214MB) — layers are compressed in the registry, expanded on disk
- Container ID in `docker ps -a` matches the hostname inside the container (`root@780a28255ef4`)
- `Exited (0)` = clean exit. Non-zero exit code = crash/error — useful for debugging
- Docker auto-generates two-word names (`naughty_shaw`) when you don't use `--name`
- `docker rmi` first untags, then deletes layers — two separate operations in the output
- Your Mac has Python 3.13.6; the container had Python 3.11.15 — same machine, zero conflict

---

## The Full Flow Visualized

```
Docker Hub
    │
    │  docker pull python:3.11-slim
    ▼
Your Mac (image stored in Docker's local cache)
    │
    │  docker run python:3.11-slim python --version
    ▼
Container (isolated process, runs command, exits)
```

---

## Summary

| Concept | What it is | Python analogy |
|---|---|---|
| Image | Read-only blueprint | Class definition |
| Container | Running instance of an image | Object (instance of a class) |
| Registry | Storage server for images | PyPI |
| Tag | Version label on an image | Package version (`==3.11`) |

---

## Key Commands Learned

```bash
docker pull <image>        # download image from registry
docker images              # list images on your machine
docker run <image> <cmd>   # create and start a container
docker run -it <image> bash  # interactive shell inside container
docker ps                  # list running containers
docker ps -a               # list all containers (including stopped)
docker rm <id>             # remove a stopped container
docker rmi <image>         # remove an image
```

---

## Check Your Understanding — Q&A

### Q1. What is the difference between an image and a container?

**Answer:** An image is a read-only blueprint (like a Python class definition).
A container is a running instance of that image (like an object instantiated
from a class). You never modify an image — you create containers from it.

---

### Q2. You run `docker run python:3.11-slim` twice. How many images? How many containers?

**Answer:** 1 image, 2 containers.

`docker run` never creates new images. It only creates container instances
from the existing image. The same blueprint spawns multiple instances.

**Common mistake:** Thinking each `docker run` creates a new image. It does not.

---

### Q3. What does `docker ps -a` show that `docker ps` does not?

**Answer:** `docker ps` shows only **running** containers.
`docker ps -a` shows ALL containers — running AND stopped.

**Why it matters:** Stopped containers still exist on disk and consume space.
`docker ps` alone will make it look like they disappeared. Always use
`docker ps -a` when debugging "missing" containers.

---

### Q4. What happens to changes you make inside a running container when it stops?

**Answer:** Changes live in the container's read-write layer.
- Container **stops** → changes are still there (container still exists)
- Container **deleted** (`docker rm`) → changes are **permanently lost**
- New container from same image → starts completely **fresh**, zero trace of previous container

**The rule:** Changes are ephemeral. They never touch the image.
The image is always read-only. Use volumes (Lesson 07) to persist data.
