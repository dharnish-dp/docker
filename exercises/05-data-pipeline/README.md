# Project 05 — Containerized Data Pipeline

## What This Project Does

A scheduled Python scraper that:
1. Fetches data from a public API every 5 minutes
2. Stores it in PostgreSQL
3. Provides a pgAdmin dashboard to explore the data

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Compose                                 │
│                                                 │
│  ┌─────────────┐    ┌──────────────────────┐   │
│  │  Scraper    │───▶│     PostgreSQL        │   │
│  │  (cron)     │    │     :5432             │◀─┐│
│  └─────────────┘    └──────────────────────┘  ││
│                                               ││
│  ┌─────────────────────────────────────────┐  ││
│  │  pgAdmin Dashboard (browser UI)  :5050  │──┘│
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
05-data-pipeline/
├── scraper/
│   ├── main.py          ← scraper script (fetches + stores data)
│   ├── database.py      ← PostgreSQL connection
│   └── models.py        ← database table definitions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# Start the pipeline
docker compose up -d

# Watch the scraper run
docker compose logs -f scraper

# Open pgAdmin dashboard in browser
open http://localhost:5050
# Email: admin@admin.com
# Password: admin
```

## Connecting pgAdmin to PostgreSQL

1. Open http://localhost:5050
2. Right-click "Servers" → Register → Server
3. General tab: Name = "Local Docker"
4. Connection tab:
   - Host: db              (service name — Docker DNS)
   - Port: 5432
   - Database: pipelinedb
   - Username: pipelineuser
   - Password: pipelinepass
5. Click Save

## Viewing the Data

In pgAdmin:
- Expand: Servers → Local Docker → Databases → pipelinedb → Schemas → public → Tables
- Right-click `weather_data` → View/Edit Data → All Rows

## What Data Is Collected

The scraper fetches weather data from Open-Meteo (free, no API key needed):
- Temperature (°C)
- Wind speed (km/h)
- Weather code
- Timestamp

Location is set to London by default — change in `scraper/main.py`.

## Stopping

```bash
docker compose down          # stop, keep data
docker compose down -v       # stop, wipe all data
```
