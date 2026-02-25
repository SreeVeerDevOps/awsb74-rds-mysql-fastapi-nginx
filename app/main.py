"""
MyFlixDB — FastAPI Movie Management API
Hosted on EC2 | Backed by AWS RDS MySQL
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import logging

from .database import engine, get_db, Base
from .models import Movie
from .schemas import (
    MovieCreate, MovieUpdate, MovieResponse,
    MovieListResponse, BulkInsertRequest, BulkInsertResponse,
    HealthResponse, MessageResponse
)
from .crud import (
    get_movie, get_movies, create_movie, update_movie,
    delete_movie, bulk_create_movies, get_movies_count
)

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="MyFlixDB API",
    description="""
## 🎬 Movie Management API

Hosted on **AWS EC2** | Backed by **AWS RDS MySQL**

### Features
- ✅ Add single or bulk movies (in increments of 10, 20, 50, 100)
- ✅ View all movies with pagination & filtering
- ✅ Update movie details
- ✅ Delete single or range of movies
- ✅ Health check with DB connectivity status
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Create tables on startup ─────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created / verified")


# ═══════════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Check API and database connectivity."""
    try:
        count = get_movies_count(db)
        return HealthResponse(
            status="healthy",
            database="connected",
            total_movies=count,
            message="MyFlixDB API is running on EC2 ✅"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# READ
# ═══════════════════════════════════════════════════════════════════

@app.get("/movies", response_model=MovieListResponse, tags=["Movies"])
def list_movies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=500, description="Max records to return"),
    director: Optional[str] = Query(None, description="Filter by director name"),
    year: Optional[int] = Query(None, description="Filter by year released"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all movies with optional filters and pagination.

    - **skip**: offset for pagination
    - **limit**: max records (up to 500)
    - **director**: partial match filter on director name
    - **year**: exact match filter on year_released
    """
    movies, total = get_movies(db, skip=skip, limit=limit, director=director, year=year)
    return MovieListResponse(
        total=total,
        skip=skip,
        limit=limit,
        data=movies
    )


@app.get("/movies/{movie_id}", response_model=MovieResponse, tags=["Movies"])
def get_single_movie(movie_id: int, db: Session = Depends(get_db)):
    """Retrieve a single movie by its ID."""
    movie = get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found")
    return movie


# ═══════════════════════════════════════════════════════════════════
# CREATE — Single
# ═══════════════════════════════════════════════════════════════════

@app.post("/movies", response_model=MovieResponse, status_code=201, tags=["Movies"])
def add_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    """
    Add a single movie to the database.

    Required fields: **title**, **director**, **year_released**
    """
    return create_movie(db, payload)


# ═══════════════════════════════════════════════════════════════════
# CREATE — Bulk (increments of 10)
# ═══════════════════════════════════════════════════════════════════

ALLOWED_BULK_SIZES = [10, 20, 30, 50, 100]

@app.post("/movies/bulk", response_model=BulkInsertResponse, status_code=201, tags=["Bulk Operations"])
def bulk_add_movies(payload: BulkInsertRequest, db: Session = Depends(get_db)):
    """
    Add multiple movies at once using **Faker-generated** data.

    **count** must be one of: `10, 20, 30, 50, 100`

    Optionally supply a list of movies manually — if provided, that list is
    used instead of auto-generation and count is ignored.
    """
    if payload.movies:
        # Manual bulk insert
        inserted = bulk_create_movies(db, payload.movies)
        return BulkInsertResponse(
            inserted=len(inserted),
            message=f"✅ {len(inserted)} movies inserted from provided list",
            movies=inserted
        )

    # Auto-generate with Faker
    if payload.count not in ALLOWED_BULK_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"count must be one of {ALLOWED_BULK_SIZES}. Got: {payload.count}"
        )
    inserted = bulk_create_movies(db, count=payload.count)
    return BulkInsertResponse(
        inserted=len(inserted),
        message=f"✅ {len(inserted)} Faker-generated movies inserted",
        movies=inserted
    )


# ═══════════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════════

@app.put("/movies/{movie_id}", response_model=MovieResponse, tags=["Movies"])
def edit_movie(movie_id: int, payload: MovieUpdate, db: Session = Depends(get_db)):
    """
    Update any fields of an existing movie.

    All fields are **optional** — only supplied fields are updated (PATCH behaviour).
    """
    movie = get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found")
    return update_movie(db, movie, payload)


# ═══════════════════════════════════════════════════════════════════
# DELETE — Single
# ═══════════════════════════════════════════════════════════════════

@app.delete("/movies/{movie_id}", response_model=MessageResponse, tags=["Movies"])
def remove_movie(movie_id: int, db: Session = Depends(get_db)):
    """Delete a single movie by ID."""
    movie = get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found")
    delete_movie(db, movie)
    return MessageResponse(message=f"🗑️ Movie ID {movie_id} deleted successfully")


# ═══════════════════════════════════════════════════════════════════
# DELETE — Range (bulk delete)
# ═══════════════════════════════════════════════════════════════════

@app.delete("/movies", response_model=MessageResponse, tags=["Bulk Operations"])
def remove_movies_above(
    above_id: int = Query(..., description="Delete all movies with ID greater than this value"),
    db: Session = Depends(get_db)
):
    """
    Delete all movies where `movie_id > above_id`.

    Example: `DELETE /movies?above_id=200` removes all records above ID 200.
    """
    deleted_count = db.query(Movie).filter(Movie.id > above_id).delete(synchronize_session=False)
    db.commit()
    return MessageResponse(message=f"🗑️ Deleted {deleted_count} movies with ID > {above_id}")
