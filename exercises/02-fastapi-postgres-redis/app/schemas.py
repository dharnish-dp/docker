"""
schemas.py — Request and response data shapes using Pydantic

Pydantic validates incoming JSON and shapes outgoing JSON.
FastAPI uses these schemas to auto-generate API documentation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemCreate(BaseModel):
    """
    Schema for creating a new item — what the client sends in the request body.
    Field() adds validation rules and documentation.
    """
    name: str = Field(..., min_length=1, max_length=100, example="Docker Book")
    description: Optional[str] = Field(None, max_length=500, example="Learn Docker in depth")
    price: float = Field(..., gt=0, example=29.99)  # gt=0 means must be greater than 0


class ItemUpdate(BaseModel):
    """Schema for updating an item — all fields optional (partial update)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)


class ItemResponse(BaseModel):
    """
    Schema for the API response — what the server sends back.
    Includes the database-generated fields (id, created_at).
    """
    id: int
    name: str
    description: Optional[str]
    price: float
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        # Allow SQLAlchemy model objects to be converted to this schema
        from_attributes = True
