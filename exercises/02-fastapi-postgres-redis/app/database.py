"""
database.py — PostgreSQL connection setup using SQLAlchemy

SQLAlchemy is Python's most popular ORM (Object Relational Mapper).
It lets you work with database tables as Python objects instead of raw SQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Build the database URL from environment variables
# Format: postgresql://user:password@host:port/dbname
# "db" is the service name in docker-compose.yml — Docker DNS resolves it
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "devpassword")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# create_engine = the connection pool to PostgreSQL
# pool_pre_ping=True = test connections before using them (handles reconnects)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal = factory that creates database sessions
# autocommit=False = we manually commit transactions (safer)
# autoflush=False = we control when queries are sent
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = parent class for all database models (tables)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency: provides a database session per request.
    The 'yield' pattern ensures the session is always closed,
    even if the request handler raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
