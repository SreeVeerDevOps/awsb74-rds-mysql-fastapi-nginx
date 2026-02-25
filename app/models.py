"""
models.py — SQLAlchemy ORM model for the movies table
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from .database import Base


class Movie(Base):
    __tablename__ = "movies"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title         = Column(String(255), nullable=False, index=True)
    director      = Column(String(255), nullable=False)
    year_released = Column(Integer, nullable=False)
    genre         = Column(String(100), nullable=True)
    rating        = Column(String(10), nullable=True)   # e.g. "PG-13", "R"
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Movie id={self.id} title='{self.title}' ({self.year_released})>"
