# Project 02 — FastAPI + PostgreSQL + Redis

## What This Project Does

A production-like REST API with:
- FastAPI — Python web framework (async, auto-generates docs)
- PostgreSQL — persistent relational database
- Redis — caching layer (repeated requests served from memory)
- Nginx — reverse proxy (handles SSL, load balancing, static files)

## Architecture

```
Browser / curl
      ↓
┌─────────────────────────────────────────────────┐
│  Docker Compose Network                         │
│                                                 │
│  ┌─────────┐    ┌──────────┐    ┌───────────┐ │
│  │  Nginx  │───▶│  FastAPI  │───▶│ PostgreSQL│ │
│  │ :80     │    │  :8000    │    │  :5432    │ │
│  └─────────┘    └──────────┘    └───────────┘ │
│                       │                         │
│                       ▼                         │
│                  ┌─────────┐                   │
│                  │  Redis  │                   │
│                  │  :6379  │                   │
│                  └─────────┘                   │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
02-fastapi-postgres-redis/
├── app/
│   ├── main.py          ← FastAPI application + routes
│   ├── database.py      ← PostgreSQL connection setup
│   ├── models.py        ← Database table definitions
│   ├── schemas.py       ← Request/response data shapes
│   └── cache.py         ← Redis caching helper
├── nginx/
│   └── nginx.conf       ← Nginx reverse proxy config
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml   ← Production overrides
├── requirements.txt
├── .env.example         ← Copy to .env and fill in values
└── README.md
```

## Quick Start

### Step 1 — Create your .env file

```bash
cp .env.example .env
# .env is already filled with safe dev defaults — no changes needed for local
```

### Step 2 — Start the stack

```bash
docker compose up -d
```

This starts: PostgreSQL → Redis → FastAPI → Nginx (in dependency order).
Wait ~10 seconds for PostgreSQL to initialise.

### Step 3 — Verify everything is running

```bash
docker compose ps
# All services should show (healthy)
```

### Step 4 — Test the API

```bash
# Create an item
curl -X POST http://localhost/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Docker Book", "price": 29.99}'

# Get all items (first call hits DB, subsequent calls hit Redis cache)
curl http://localhost/items

# Get one item
curl http://localhost/items/1

# Interactive API docs (open in browser)
open http://localhost/docs
```

### Step 5 — View logs

```bash
docker compose logs -f app      # FastAPI logs
docker compose logs -f db       # PostgreSQL logs
docker compose logs -f redis    # Redis logs
```

### Step 6 — Stop

```bash
docker compose down          # stop, keep data
docker compose down -v       # stop, wipe database
```

## Accessing the Database Directly

```bash
docker compose exec db psql -U appuser -d appdb
# Inside psql:
\dt                          # list tables
SELECT * FROM items;         # query data
\q                           # quit
```

## Accessing Redis Directly

```bash
docker compose exec redis redis-cli
# Inside redis-cli:
KEYS *                       # list all cached keys
GET items:all                # view cached value
TTL items:all                # seconds until cache expires
FLUSHALL                     # clear all cache
```

## What the Caching Does

```
First request  GET /items → hits PostgreSQL → stores result in Redis (60s TTL)
Second request GET /items → hits Redis      → response in <1ms (no DB query)
After 60s      GET /items → Redis expired   → hits PostgreSQL again
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | appuser | Database username |
| `POSTGRES_PASSWORD` | devpassword | Database password |
| `POSTGRES_DB` | appdb | Database name |
| `REDIS_HOST` | redis | Redis hostname (service name) |
| `REDIS_TTL` | 60 | Cache TTL in seconds |
| `API_SECRET_KEY` | dev-secret | JWT signing key (change in prod!) |
