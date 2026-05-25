"""models.py — Database table for weather data"""
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from scraper.database import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(100), nullable=False)
    temperature_c = Column(Float)
    wind_speed_kmh = Column(Float)
    weather_code = Column(Integer)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
