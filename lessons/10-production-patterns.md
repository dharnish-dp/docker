# Lesson 10 — Production Patterns

## Goal
Make containers reliable in production — handle crashes, signal shutdown
correctly, scale safely, and debug without guessing.

## Prerequisites
Lessons 04, 08, 09 — Dockerfile, Compose, Security

## After This Lesson You Will Be Able To
- Add health checks to any container and use them in Compose dependencies
- Write Python code that handles SIGTERM for graceful shutdown
- Set restart policies so containers recover automatically from crashes
- Set resource limits to protect the host from runaway containers
- Configure logging to stdout for Docker-native log collection
- Tag images correctly so production deployments are reproducible

---

## Production Readiness Checklist

```
✅ Container signals when it's actually ready (health check)
✅ Container shuts down cleanly without dropping requests (graceful shutdown)
✅ Container restarts itself if it crashes (restart policy)
✅ Container has resource limits (memory + CPU)
✅ Container logs go to stdout (not files)
✅ Image is pinned to a specific version (not latest)
```

---

## Pattern 1 — Health Checks

A container showing "running" does NOT mean your app is ready.
The app could be initialising, deadlocked, or silently crashed.

A health check is a command Docker runs periodically to verify
your app is actually responding.

```
Without healthcheck:
  Status = "Up 2 minutes"  ← app could be broken, nobody knows

With healthcheck:
  Status = "Up 2 minutes (healthy)"    ← app verified working
  Status = "Up 2 minutes (unhealthy)"  ← app broken, alerts fire
```

### Health Check in Dockerfile

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"
```

Every flag explained:

```
--interval=30s     → run the check every 30 seconds
--timeout=5s       → if check takes longer than 5s → count as failed
--retries=3        → after 3 consecutive failures → mark "unhealthy"
--start-period=10s → grace period before counting failures
                    (prevents false unhealthy during slow startup)
CMD <command>      → exit 0 = healthy, any other exit code = unhealthy
```

### Health Check in Docker Compose

```yaml
services:
  app:
    build: .
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  worker:
    depends_on:
      app:
        condition: service_healthy   # wait until app is HEALTHY, not just started
```

### Check Health Status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
# NAMES       STATUS
# webserver   Up 2 minutes (healthy)    ← passing ✅
# webserver   Up 2 minutes (unhealthy)  ← failing ❌

docker inspect --format "{{.State.Health.Status}}" <container>
# healthy / unhealthy / starting
```

---

## Pattern 2 — Graceful Shutdown

`docker stop` sends **SIGTERM** to PID 1. The app has 10 seconds to
finish in-flight work and exit cleanly. After 10s, Docker sends SIGKILL
— immediate termination, no cleanup, connections dropped.

### Why Shell Form Breaks Shutdown (Critical)

```dockerfile
# SHELL FORM — broken ❌
CMD python server.py
# Docker runs: /bin/sh -c "python server.py"
# PID 1 = /bin/sh  ← SIGTERM goes here
# PID 2 = python   ← your app, never receives SIGTERM
# sh ignores SIGTERM — Python gets SIGKILL after 10s
```

```dockerfile
# EXEC FORM — correct ✅
CMD ["python", "server.py"]
# Docker runs: python server.py directly
# PID 1 = python server.py  ← SIGTERM goes directly to your app
```

**Always use exec form `["cmd", "arg"]` for CMD and ENTRYPOINT.**

### Handling SIGTERM in Python

```python
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

server = None

def handle_shutdown(signum, frame):
    print("SIGTERM received — shutting down gracefully...")
    if server:
        server.server_close()   # stop accepting new connections
    sys.exit(0)                 # exit with code 0 (clean exit)

# Register BEFORE starting the server
signal.signal(signal.SIGTERM, handle_shutdown)  # docker stop
signal.signal(signal.SIGINT, handle_shutdown)   # Ctrl+C

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello!")

server = HTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever()
```

### Adjust the Shutdown Timeout

Default is 10 seconds. For apps that need more time:

```bash
docker stop --time 30 <container>   # give 30 seconds before SIGKILL
```

In Docker Compose:
```yaml
services:
  app:
    stop_grace_period: 30s   # wait 30s before SIGKILL
```

---

## Pattern 3 — Restart Policies

Without a restart policy, crashed containers stay dead until someone
manually restarts them.

```bash
docker run --restart unless-stopped myimage
```

| Policy | When it restarts | Use case |
|---|---|---|
| `no` | Never | Default — one-shot scripts |
| `always` | Always, even on clean exit | Services that must always run |
| `unless-stopped` | On crash/reboot, NOT after manual stop | **Production default** |
| `on-failure` | Only on non-zero exit code | Services that should only retry on error |
| `on-failure:3` | Max 3 times on failure, then stop | Prevent infinite crash loops |

**`unless-stopped` is correct for production services:**
- Survives container crashes ✅
- Survives Docker daemon restarts and host reboots ✅
- Respects intentional `docker stop` (deployments, maintenance) ✅

In Docker Compose:
```yaml
services:
  app:
    restart: unless-stopped

  one-shot-job:
    restart: "no"   # quotes required — no is a YAML boolean without them
```

---

## Pattern 4 — Resource Limits

Without limits, one container can consume 100% CPU and RAM — crashing
the host and taking down every other container with it.

```bash
docker run --memory 512m --cpus 1.0 myimage
```

In Docker Compose:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512m    # hard ceiling — container cannot exceed this
          cpus: "1.0"     # max 1 CPU core
        reservations:
          memory: 256m    # guaranteed minimum — always available
          cpus: "0.5"
```

**What happens when limits are hit:**
- Memory exceeded → kernel OOM-kills the container → `Exited (137)`
- CPU exceeded → kernel throttles (slows down) — container stays alive

**Rule: always set `--memory` in production.** CPU throttling is
recoverable; OOM kills are not.

---

## Pattern 5 — Log to stdout

Never write logs to files inside a container. Always write to `stdout`
and `stderr`.

```python
# WRONG — log file inside ephemeral container
import logging
logging.basicConfig(filename='/var/log/app.log')

# CORRECT — stdout/stderr
import logging
logging.basicConfig(level=logging.INFO)   # writes to stderr
print("something happened")               # writes to stdout
```

**Why stdout?**

```
App → stdout/stderr → Docker captures automatically
                    → docker logs <container>         (local viewing)
                    → log driver → ELK / Datadog      (production shipping)
                    → log driver → CloudWatch / Splunk
```

Docker captures everything from stdout/stderr automatically. Configure
a log driver to ship logs to your central logging system. The container
stays stateless — no log files to manage, rotate, or clean up.

```bash
docker logs <container>           # view all logs
docker logs -f <container>        # follow in real time (like tail -f)
docker logs --tail 50 <container> # last 50 lines only
docker logs --since 10m <container> # logs from last 10 minutes
```

---

## Pattern 6 — Pin Image Versions

```bash
# WRONG — "latest" changes without warning, unreproducible
docker run myapp:latest

# CORRECT — pinned semantic version
docker run myapp:1.4.2

# MOST CORRECT — pinned to digest, 100% immutable
docker run myapp@sha256:9a7765b36773a37061455b332f18e265e7f58f6fea9c419a550d2a8b0e9db834
```

**Why `latest` is dangerous in production:**
- `latest` = most recently pushed tag — changes whenever anyone pushes
- Two deploys of `myapp:latest` a week apart may run completely different code
- Cannot roll back — you don't know what version you had before

**Tagging strategies:**

```bash
# Option 1 — semantic version (human readable)
docker build -t myapp:1.4.2 .

# Option 2 — git commit hash (tied to exact code)
docker build -t myapp:$(git rev-parse --short HEAD) .

# Option 3 — both (best — semantic + traceable)
docker build -t myapp:1.4.2 -t myapp:$(git rev-parse --short HEAD) .
```

---

## The Production-Ready Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

RUN chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "app.py"]
```

## The Production-Ready docker run

```bash
docker run \
  --restart unless-stopped \          # auto-recover from crashes
  --memory 512m \                     # cap RAM
  --cpus 1.0 \                        # cap CPU
  --read-only \                       # lock filesystem
  --tmpfs /tmp \                      # writable RAM for temp files
  --cap-drop ALL \                    # remove all capabilities
  --security-opt no-new-privileges \  # block privilege escalation
  --user 1001:1001 \                  # non-root
  -p 8080:8080 \                      # expose port
  myapp:1.4.2                         # pinned version
```

---

## Command Reference — Every Command Explained

---

### `docker ps --format "table {{.Names}}\t{{.Status}}"`

```
docker ps          → list running containers
--format           → customize output format instead of default table
"table ..."        → "table" keyword = print a header row automatically
{{.Names}}         → Go template field: container name
\t                 → tab character (separates columns)
{{.Status}}        → Go template field: status including health state
                    e.g. "Up 2 minutes (healthy)" or "Up 2 minutes (unhealthy)"
```

Other useful format fields:
```bash
{{.ID}}            → container ID
{{.Image}}         → image name
{{.Ports}}         → mapped ports
{{.CreatedAt}}     → when created
```

---

### `docker inspect --format "{{.State.Health.Status}}" <container>`

```
docker inspect     → outputs full JSON metadata of a container (very verbose)
--format           → extract just one field from the JSON instead of printing all
"{{.State.Health.Status}}"  → Go template: navigate JSON path State → Health → Status
                    Returns: "healthy", "unhealthy", or "starting"
<container>        → container name or ID
```

For more health detail:
```bash
docker inspect --format "{{json .State.Health}}" <container>
# Returns full JSON: last check time, log of last 5 checks, failure count
```

---

### `docker stop --time 30 <container>`

```
docker stop        → send SIGTERM to PID 1, wait for clean exit
--time 30          → wait 30 seconds before sending SIGKILL (default is 10s)
                    Use for apps that need extra time to finish in-flight work
                    e.g. database flushing writes, HTTP server draining connections
<container>        → container name or ID
```

---

### `docker logs -f <container>`

```
docker logs        → print all captured stdout/stderr from a container
-f                 → follow: stream new log lines in real time (like tail -f)
                    Press Ctrl+C to stop following
<container>        → container name or ID
```

Useful variants:
```bash
docker logs --tail 50 <container>     # only last 50 lines
docker logs --since 10m <container>   # logs from last 10 minutes
docker logs --since 2026-05-01 <container>  # logs since specific date
docker logs --until 10m <container>   # logs older than 10 minutes ago
```

---

### `docker logs --since 10m <container>`

```
--since 10m        → only show logs from the last 10 minutes
                    Format: <number><unit> where unit = s, m, h
                    Examples: --since 30s, --since 2h, --since 1h30m
                    Also accepts absolute timestamps: --since 2026-05-01T10:00:00
```

---

### `docker stats`

```
docker stats       → live dashboard of resource usage for ALL running containers
                    Updates every second. Shows:
                    - CPU %        → current CPU usage
                    - MEM USAGE    → current memory / limit
                    - MEM %        → memory as percentage of limit
                    - NET I/O      → total network bytes sent/received
                    - BLOCK I/O    → total disk bytes read/written
                    - PIDS         → number of processes inside container
```

```bash
docker stats <container>   # single container only
docker stats --no-stream   # one snapshot, then exit (don't keep updating)
```

Use `docker stats` to confirm OOM (memory at 100% before exit code 137).

---

### `pip install --no-cache-dir -r requirements.txt`

```
pip install        → install Python packages
--no-cache-dir     → don't save downloaded packages to pip's cache
                    Reduces image layer size — the cache would be baked in
                    Use this in Dockerfiles without cache mounts
                    (If using --mount=type=cache, omit this flag — the cache mount handles it)
-r requirements.txt → install all packages listed in requirements.txt
```

---

### `docker build -t myapp:$(git rev-parse --short HEAD) .`

```
docker build       → build an image
-t myapp:...       → tag the image
$(...)             → shell command substitution — runs the command and inserts output
git rev-parse      → git command: convert a ref to the full SHA hash
--short            → return only the first 7 characters (e.g. "a3f9b12")
HEAD               → the current commit
```

Result: image is tagged with the exact git commit that built it.
```bash
myapp:a3f9b12   → traceable to a specific commit in git history
```

---

### `signal.signal(signal.SIGTERM, handle_shutdown)`

```python
signal.signal(     # register a function to call when a signal arrives
  signal.SIGTERM,  # the signal to listen for:
                   # SIGTERM = "please shut down" (sent by docker stop)
                   # SIGINT  = Ctrl+C (sent by terminal)
                   # SIGKILL = cannot be caught — immediate termination
  handle_shutdown  # the function to call when SIGTERM is received
)
```

The handler function signature:
```python
def handle_shutdown(signum, frame):
    # signum = the signal number (15 for SIGTERM, 2 for SIGINT)
    # frame  = current stack frame at the time signal arrived (rarely used)
    pass
```

---

## Check Your Understanding — Q&A

### Q1. Your Compose file has `depends_on: db`. Why might your app still fail to connect to the database on startup?

**Answer:** `depends_on` by default only waits for the database container to
**start** — not for Postgres to be ready to accept connections. Postgres takes
several seconds to initialise after the container starts. Use
`condition: service_healthy` with a healthcheck on the db service to wait
until Postgres is actually ready.

---

### Q2. You run `docker stop myapp` and it takes exactly 10 seconds. What happened?

**Answer:** Your app did not handle SIGTERM. Docker sent SIGTERM, waited the
default 10-second grace period, then sent SIGKILL to force-terminate. This
likely means either the CMD uses shell form (so Python is not PID 1), or the
Python code has no `signal.signal(signal.SIGTERM, ...)` handler.

---

### Q3. What is the difference between `restart: always` and `restart: unless-stopped`?

**Answer:** `always` restarts even after a manual `docker stop`. If you stop
a container for maintenance or deployment, it immediately restarts — you can
never keep it stopped. `unless-stopped` respects manual stops — it restarts
on crashes and reboots, but stays stopped if you explicitly stopped it.
Always use `unless-stopped` for production services.

---

### Q4. Your container exits with code 137. What happened and how do you fix it?

**Answer:** Exit code 137 = killed by the kernel's OOM (Out of Memory) killer.
The container exceeded its `--memory` limit. Fix options:
1. Increase the memory limit if the app legitimately needs more
2. Find and fix the memory leak in your code
3. Add `--memory-swap` to allow swapping (last resort — much slower)
Run `docker stats` before the crash to confirm memory is the cause.
