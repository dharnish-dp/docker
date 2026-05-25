# Project 01 — Containerized Selenium Test Suite

## What This Project Does

Runs a Selenium test suite inside Docker with headless Chrome.
No browser installation needed on your machine or any CI server.
Test reports are saved back to your Mac via bind mount.

## Architecture

```
┌─────────────────────────────────────────┐
│  Docker Container                       │
│                                         │
│  Python 3.11                           │
│  Selenium + ChromeDriver               │
│  Chrome (headless, no display needed)  │
│                                         │
│  /app/tests/          ← your tests     │
│  /app/reports/        ← HTML reports   │
└─────────────────────────────────────────┘
         ↕ bind mount
┌─────────────────────────────────────────┐
│  Your Mac                               │
│  ./reports/           ← reports appear │
└─────────────────────────────────────────┘
```

## Project Structure

```
01-selenium-test-suite/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── tests/
│   ├── test_google.py      ← example: search on Google
│   └── test_httpbin.py     ← example: test an API-like site
├── reports/                ← HTML reports saved here (auto-created)
└── README.md
```

## How to Run

### Option 1 — Single run (one command)

```bash
# From this directory
docker compose run --rm tests
```

This builds the image, runs all tests, saves reports, then cleans up.

### Option 2 — Run specific test file

```bash
docker compose run --rm tests pytest tests/test_google.py -v
```

### Option 3 — Run with live output

```bash
docker compose run --rm tests pytest tests/ -v --tb=short
```

### Option 4 — Interactive shell (for debugging)

```bash
docker compose run --rm tests bash
# Inside container:
pytest tests/test_google.py -v -s
```

## View Reports

After running tests, open the HTML report:

```bash
open reports/report.html    # Mac: opens in your browser
```

## Adding Your Own Tests

1. Create a new file in `tests/` following the naming pattern `test_*.py`
2. Use the `driver` fixture from `conftest.py` (provided automatically)
3. Run with `docker compose run --rm tests`

Example test:

```python
def test_my_site(driver):
    driver.get("https://example.com")
    assert "Example" in driver.title
```

## Changing Chrome Options

Edit `tests/conftest.py` to add Chrome flags:

```python
options.add_argument("--window-size=1920,1080")  # set viewport
options.add_argument("--lang=en-US")              # set language
```
