"""
main.py — Data pipeline scraper

Fetches weather data from Open-Meteo API every 5 minutes
and stores it in PostgreSQL.

Open-Meteo is free, no API key needed.
Docs: https://open-meteo.com/en/docs
"""
import time
import schedule
import requests
import logging
from scraper.database import engine, SessionLocal, Base
from scraper.models import WeatherData

# Log to stdout — Docker captures this automatically
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────
# London coordinates — change to your city
LATITUDE = 51.5074
LONGITUDE = -0.1278
LOCATION_NAME = "London"

API_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&current_weather=true"
)


# ── Scraper ───────────────────────────────────────────────────────
def fetch_and_store():
    """
    Fetches current weather and stores one row in PostgreSQL.
    Called every 5 minutes by the scheduler.
    """
    log.info(f"Fetching weather for {LOCATION_NAME}...")

    try:
        # Fetch from Open-Meteo API
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()  # raise exception for 4xx/5xx responses
        data = response.json()

        weather = data["current_weather"]

        # Store in database
        db = SessionLocal()
        try:
            record = WeatherData(
                location=LOCATION_NAME,
                temperature_c=weather["temperature"],
                wind_speed_kmh=weather["windspeed"],
                weather_code=weather["weathercode"]
            )
            db.add(record)
            db.commit()

            log.info(
                f"Stored: {LOCATION_NAME} | "
                f"Temp: {weather['temperature']}°C | "
                f"Wind: {weather['windspeed']} km/h"
            )
        finally:
            db.close()

    except requests.RequestException as e:
        # Network errors — log and continue (scheduler will retry)
        log.error(f"API request failed: {e}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")


# ── Startup ───────────────────────────────────────────────────────
def wait_for_db(max_retries=10):
    """Wait for PostgreSQL to be ready before starting."""
    from sqlalchemy import text
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("Database is ready")
            return
        except Exception:
            log.info(f"Waiting for database... ({attempt + 1}/{max_retries})")
            time.sleep(3)
    raise RuntimeError("Database not available after retries")


if __name__ == "__main__":
    log.info("Data pipeline starting...")

    # Wait for DB to be ready
    wait_for_db()

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    log.info("Tables ready")

    # Run once immediately on startup
    fetch_and_store()

    # Schedule to run every 5 minutes
    schedule.every(5).minutes.do(fetch_and_store)
    log.info("Scheduler started — fetching every 5 minutes")

    # Keep running forever
    while True:
        schedule.run_pending()
        time.sleep(1)
