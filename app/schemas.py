"""
schemas.py — Pydantic models for request validation and response serialisation
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


# ── Movie payloads ────────────────────────────────────────────────────

class MovieBase(BaseModel):
    title: str         = Field(..., min_length=1, max_length=255, example="The Matrix")
    director: str      = Field(..., min_length=1, max_length=255, example="Lana Wachowski")
    year_released: int = Field(..., ge=1888, le=2099,             example=1999)
    genre: Optional[str]  = Field(None, max_length=100,           example="Sci-Fi")
    rating: Optional[str] = Field(None, max_length=10,            example="R")

    @validator("year_released")
    def year_must_be_reasonable(cls, v):
        if not (1888 <= v <= 2099):
            raise ValueError("year_released must be between 1888 and 2099")
        return v


class MovieCreate(MovieBase):
    """Payload to create a single movie."""
    pass


class MovieUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    title:         Optional[str] = Field(None, min_length=1, max_length=255)
    director:      Optional[str] = Field(None, min_length=1, max_length=255)
    year_released: Optional[int] = Field(None, ge=1888, le=2099)
    genre:         Optional[str] = Field(None, max_length=100)
    rating:        Optional[str] = Field(None, max_length=10)


class MovieResponse(MovieBase):
    """Full movie record returned from the API."""
    id:         int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True   # SQLAlchemy ORM → Pydantic


class MovieListResponse(BaseModel):
    total: int
    skip:  int
    limit: int
    data:  List[MovieResponse]


# ── Bulk insert ───────────────────────────────────────────────────────

class BulkInsertRequest(BaseModel):
    """
    Bulk movie insert.

    - Set **count** to 10 / 20 / 30 / 50 / 100 to auto-generate records with Faker.
    - OR supply a **movies** list to insert specific records (count is ignored).
    """
    count:  int                        = Field(10,  description="Auto-generate N movies (10/20/30/50/100)")
    movies: Optional[List[MovieCreate]] = Field(None, description="Manual list of movies to insert")


class BulkInsertResponse(BaseModel):
    inserted: int
    message:  str
    movies:   List[MovieResponse]


# ── Utility responses ─────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status:        str
    database:      str
    total_movies:  int
    message:       str
