"""
crud.py — Database CRUD operations
"""

from typing import List, Optional, Tuple
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import Movie
from .schemas import MovieCreate, MovieUpdate

fake = Faker()

GENRES  = ["Action","Comedy","Drama","Sci-Fi","Thriller","Horror","Romance","Documentary","Animation","Fantasy"]
RATINGS = ["G","PG","PG-13","R","NC-17","NR"]


# ── Helpers ───────────────────────────────────────────────────────────

def get_movies_count(db: Session) -> int:
    return db.query(Movie).count()


# ── Read ──────────────────────────────────────────────────────────────

def get_movie(db: Session, movie_id: int) -> Optional[Movie]:
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_movies(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    director: Optional[str] = None,
    year: Optional[int] = None,
) -> Tuple[List[Movie], int]:
    query = db.query(Movie)

    if director:
        query = query.filter(Movie.director.ilike(f"%{director}%"))
    if year:
        query = query.filter(Movie.year_released == year)

    total = query.count()
    movies = query.order_by(Movie.id.desc()).offset(skip).limit(limit).all()
    return movies, total


# ── Create — single ───────────────────────────────────────────────────

def create_movie(db: Session, payload: MovieCreate) -> Movie:
    movie = Movie(**payload.dict())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


# ── Create — bulk ─────────────────────────────────────────────────────

def _fake_movie() -> MovieCreate:
    """Generate a realistic fake movie record."""
    return MovieCreate(
        title         = fake.catch_phrase().title(),
        director      = fake.name(),
        year_released = fake.random_int(min=1970, max=2024),
        genre         = fake.random_element(GENRES),
        rating        = fake.random_element(RATINGS),
    )


def bulk_create_movies(
    db: Session,
    movies: Optional[List[MovieCreate]] = None,
    count: int = 10,
) -> List[Movie]:
    """
    Insert multiple movies.
    If `movies` list provided → insert those.
    Otherwise auto-generate `count` records with Faker.
    """
    records = movies if movies else [_fake_movie() for _ in range(count)]

    db_movies = [Movie(**m.dict()) for m in records]
    db.bulk_save_objects(db_movies, return_defaults=True)
    db.commit()

    # Re-query to get auto-assigned IDs
    # Bulk save doesn't populate IDs, so fetch the most recent N rows
    inserted = (
        db.query(Movie)
        .order_by(Movie.id.desc())
        .limit(len(db_movies))
        .all()
    )
    return list(reversed(inserted))


# ── Update ────────────────────────────────────────────────────────────

def update_movie(db: Session, movie: Movie, payload: MovieUpdate) -> Movie:
    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(movie, field, value)
    db.commit()
    db.refresh(movie)
    return movie


# ── Delete — single ───────────────────────────────────────────────────

def delete_movie(db: Session, movie: Movie) -> None:
    db.delete(movie)
    db.commit()
