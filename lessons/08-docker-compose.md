# Lesson 08 — Docker Compose

## Goal
Manage multi-container applications with a single YAML file instead of
multiple long `docker run` commands.

## Prerequisites
Lessons 04, 06, 07 — Dockerfile, Networking, Storage (Compose combines all three)

## After This Lesson You Will Be Able To
- Write a `docker-compose.yml` for any multi-container application
- Start and stop an entire application stack with one command
- Use every Compose keyword (services, networks, volumes, depends_on, etc.)
- Run services in background and read their logs

---

## The Problem

Running two containers manually is already messy:

```bash
docker network create my-network
docker run -d --name redis --network my-network -v redisdata:/data redis:7
docker run -d --name myapp --network my-network -e REDIS_HOST=redis myapp:1.0
```

A real app has 4-6 services. That's 6 commands to remember, run in the right
order, and clean up manually. Docker Compose solves this with one file.

---

## What Docker Compose Is

A YAML wrapper around docker commands you already know.

```
docker-compose.yml   →   docker compose up   →   Docker runs:
                                                   docker network create ...
                                                   docker volume create ...
                                                   docker run ... (per service)
```

Everything in Compose maps to flags you already know:

| Compose key | Equivalent flag |
|---|---|
| `image:` | image name |
| `build:` | build from Dockerfile |
| `ports:` | `-p` |
| `volumes:` | `-v` |
| `environment:` | `-e` |
| `networks:` | `--network` |
| `depends_on:` | start order |

---

## docker-compose.yml Structure

```yaml
services:
  app:
    build: .                    # build from Dockerfile in current folder
    networks:
      - app-network
    depends_on:
      - redis                   # start redis BEFORE app

  redis:
    image: redis:7-alpine       # pull from registry
    networks:
      - app-network
    volumes:
      - redisdata:/data         # persist Redis data

networks:
  app-network:                  # Compose creates this custom bridge network

volumes:
  redisdata:                    # Compose creates this named volume
```

---

## What We Built

A Python script that connects to Redis, writes 3 values, and reads them back.

**app.py**
```python
import redis

client = redis.Redis(host="redis", port=6379, decode_responses=True)
client.set("name", "Docker Compose")
client.incr("run_count")
print(f"run_count = {client.get('run_count')}")
```

`host="redis"` works because Compose puts both services on the same custom
network — Docker DNS resolves the service name `redis` to its container IP.

---

## Compose Naming Convention

Compose prefixes all resources with the project folder name:

```
Folder: compose-demo/
Network:   compose-demo_app-network
Volume:    compose-demo_redisdata
Container: compose-demo-redis-1
Container: compose-demo-app-1
```

This prevents name clashes between multiple Compose projects.

---

## All Keywords Explained

### `services`
The top-level key. Every container in your application is a service.
Each service becomes one container when Compose runs.

```yaml
services:
  app:      # service name — also its DNS hostname on the network
  redis:
  postgres:
```

---

### `image` vs `build`

```yaml
services:
  redis:
    image: redis:7-alpine      # pull this image from a registry

  app:
    build: .                   # build from Dockerfile in current directory
    # OR with more control:
    build:
      context: .               # where to find files (build context)
      dockerfile: Dockerfile   # which Dockerfile to use
```

---

### `ports`

```yaml
ports:
  - "8080:80"       # host_port:container_port
  - "5432:5432"     # same port on both sides
  - "127.0.0.1:8080:80"  # bind to specific host IP only (more secure)
```

Only needed when your Mac/browser needs to reach the container.
Container-to-container communication does NOT need ports.

---

### `environment`

Two formats — both work:

```yaml
# List format (common)
environment:
  - DB_HOST=postgres
  - DB_PORT=5432
  - DEBUG=true

# Map format (cleaner)
environment:
  DB_HOST: postgres
  DB_PORT: 5432
  DEBUG: "true"
```

These become environment variables inside the container — same as `-e` in `docker run`.

---

### `.env` file — automatic variable injection

Create a `.env` file in the same folder as `docker-compose.yml`:

```bash
# .env
DB_PASSWORD=secret123
REDIS_PORT=6379
```

Reference in `docker-compose.yml`:

```yaml
environment:
  - DB_PASSWORD=${DB_PASSWORD}
  - REDIS_PORT=${REDIS_PORT}
```

Compose loads `.env` automatically. Never commit `.env` to git — add it to `.gitignore`.

---

### `volumes`

```yaml
services:
  redis:
    volumes:
      - redisdata:/data          # named volume → Docker manages location
      - ./config:/etc/redis      # bind mount → your Mac folder
      - /tmp/cache:/cache        # bind mount → absolute path

volumes:
  redisdata:                     # declare named volumes at bottom of file
```

---

### `networks`

```yaml
services:
  app:
    networks:
      - frontend
      - backend          # app is on TWO networks

  redis:
    networks:
      - backend          # redis only on backend — app can reach it, browser cannot

networks:
  frontend:
  backend:
```

This is how you isolate services — database only on internal network,
web server on both internal and external.

---

### `depends_on`

```yaml
services:
  app:
    depends_on:
      - redis            # basic: just waits for container to START
      - postgres

  # Advanced: wait for service to be HEALTHY (needs healthcheck)
  app:
    depends_on:
      postgres:
        condition: service_healthy   # waits until healthcheck passes
      redis:
        condition: service_started   # just waits for start (default)
```

---

### `restart`

```yaml
restart: "no"             # never restart (default)
restart: always           # always restart, even on clean exit
restart: unless-stopped   # restart unless manually stopped (production default)
restart: on-failure       # restart only on non-zero exit code
restart: on-failure:3     # restart max 3 times on failure
```

---

### `container_name`

```yaml
services:
  redis:
    container_name: my-redis    # fixed name instead of compose-demo-redis-1
```

Use sparingly — fixed names can clash if you run multiple instances.

---

### `healthcheck`

```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s      # check every 10s
      timeout: 5s        # fail if no response in 5s
      retries: 3         # mark unhealthy after 3 failures
      start_period: 30s  # grace period before checks start
```

Used with `depends_on: condition: service_healthy` to wait until a service
is truly ready, not just started. Covered in depth in Lesson 10.

---

### `profiles`

Mark optional services that only start when explicitly requested:

```yaml
services:
  app:
    image: myapp:1.0            # always starts

  debug-tools:
    image: busybox
    profiles: ["debug"]         # only starts with: docker compose --profile debug up
```

---

## Key Commands

```bash
# Starting and stopping
docker compose up                    # start all services (foreground)
docker compose up -d                 # start in background (detached)
docker compose up --build            # rebuild images then start
docker compose up --build -d         # rebuild + start in background
docker compose down                  # stop + remove containers + network
docker compose down -v               # also remove volumes (wipes data)
docker compose stop                  # stop containers (don't remove)
docker compose start                 # start stopped containers
docker compose restart               # restart all services

# Status and logs
docker compose ps                    # list services and status
docker compose logs                  # all logs from all services
docker compose logs -f               # follow logs in real time
docker compose logs app              # logs for one specific service
docker compose logs -f redis         # follow one service

# Running commands
docker compose exec app bash         # shell into a running service
docker compose exec redis redis-cli  # run a command in running service
docker compose run --rm app python test.py  # run one-off command in new container

# Building
docker compose build                 # rebuild all images
docker compose build app             # rebuild one service image
docker compose pull                  # pull latest images from registry

# Validation
docker compose config                # validate and view merged config

# Profiles
docker compose --profile debug up    # start with optional services
```

---

## Long-running vs One-shot Services

```
redis:   stays running forever (server)       → shows in docker compose ps
app:     runs script and exits (one-shot)     → not in docker compose ps (exited)
```

One-shot containers exit with code 0 = success. Still visible in `docker compose logs`.

---

## Volume Behaviour with Compose

```bash
docker compose down         # volumes KEPT  → data survives
docker compose down -v      # volumes DELETED → data wiped (use in CI/dev reset)
```

`down -v` is for clean resets. Never use it on production data.

---

## Check Your Understanding — Q&A

### Q1. What does `depends_on` do?

**Answer:** It tells Compose to start one service before another.
`depends_on: redis` means Redis container starts before the app container.
It does NOT wait for Redis to be ready — just that the container has started.
For true readiness checks, you need `healthcheck` (covered in Lesson 10).

---

### Q2. How does `host="redis"` work in the Python code with no IP address?

**Answer:** Compose automatically creates a custom bridge network and attaches
all services to it. Docker's built-in DNS resolves service names to their
container IPs. `redis` in the Python code resolves to the Redis container's
internal IP — exactly like Lesson 6's custom network, but set up automatically.

---

### Q3. What is the difference between `docker compose down` and `docker compose down -v`?

**Answer:**
- `docker compose down` → removes containers and network, keeps volumes
- `docker compose down -v` → removes everything including volumes (data gone permanently)

Use `down` in normal dev work. Use `down -v` only for a clean reset.

---

### Q4. The app container exits immediately after running. Is that a problem?

**Answer:** No — it depends on the service type. A Python script that runs
once and exits is a one-shot task. Exit code 0 = success. A database or web
server is expected to stay running indefinitely. Compose handles both patterns.
The issue would only be an unexpected non-zero exit code (crash).
