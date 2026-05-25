"""
main.py — FastAPI application

FastAPI automatically generates interactive API docs at /docs
Run: uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import engine, get_db, Base
from app.models import Item
from app.schemas import ItemCreate, ItemUpdate, ItemResponse
from app.cache import cache_get, cache_set, cache_delete_pattern

# Create all database tables on startup
# In production, use Alembic migrations instead
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Items API",
    description="A production-like REST API with PostgreSQL and Redis caching",
    version="1.0.0"
)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """
    Health check endpoint — used by Docker HEALTHCHECK.
    Returns 200 OK when the app is ready to serve requests.
    """
    return {"status": "healthy"}


# ── Items CRUD ────────────────────────────────────────────────────────────────

@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item.

    Depends(get_db) = FastAPI injects a database session automatically.
    After creating, we clear the items cache so next GET returns fresh data.
    """
    db_item = Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Invalidate cache — new item was added
    cache_delete_pattern("items:*")

    return db_item


@app.get("/items", response_model=List[ItemResponse])
def get_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all items.

    Cache strategy:
    1. Check Redis cache first
    2. If cache hit → return cached data (fast, no DB query)
    3. If cache miss → query DB, store in cache, return data
    """
    cache_key = f"items:all:{skip}:{limit}"

    # Try cache first
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Cache miss — query database
    items = db.query(Item).offset(skip).limit(limit).all()

    # Convert SQLAlchemy objects to dicts for JSON serialization
    items_data = [ItemResponse.model_validate(item).model_dump() for item in items]

    # Store in cache for next request
    cache_set(cache_key, items_data)

    return items


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single item by ID."""
    cache_key = f"items:{item_id}"

    cached = cache_get(cache_key)
    if cached:
        return cached

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    item_data = ItemResponse.model_validate(item).model_dump()
    cache_set(cache_key, item_data)

    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, updates: ItemUpdate, db: Session = Depends(get_db)):
    """Update an existing item."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # Only update fields that were actually provided
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    # Invalidate this item's cache and the all-items cache
    cache_delete_pattern("items:*")

    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    db.delete(item)
    db.commit()

    cache_delete_pattern("items:*")
