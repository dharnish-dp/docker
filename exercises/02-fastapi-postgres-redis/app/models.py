"""
models.py — Database table definitions

Each class here maps to one table in PostgreSQL.
SQLAlchemy creates the tables automatically on startup.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    """
    The 'items' table in PostgreSQL.

    __tablename__ = the actual table name in the database
    Each Column() = one column in the table
    """
    __tablename__ = "items"

    # Integer primary key — auto-increments with each new row
    id = Column(Integer, primary_key=True, index=True)

    # String columns — index=True adds a DB index for faster lookups
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    # Float for price — use Numeric(10,2) in production for exact decimals
    price = Column(Float, nullable=False)

    # Automatically set to current time when row is created
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Automatically updated when row is modified
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
