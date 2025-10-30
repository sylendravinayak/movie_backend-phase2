from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from . import ORMModel


# 2. MOVIE
class MovieBase(ORMModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    duration: int = Field(..., description="Duration in minutes")
    genre: Optional[list[str]] = Field(None, description="List of genres")
    language: Optional[list[str]] = Field(None, description="List of languages")
    release_date: Optional[date] = None
    rating: Optional[float] = Field(
        None, description="e.g., 4.5 out of 5.0"
    )
    certificate: Optional[str] = Field(None, max_length=10)
    poster_url: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    cast: Optional[list[dict]] = None
    crew: Optional[list[dict]] = None


class MovieCreate(MovieBase):
    pass


class MovieUpdate(ORMModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    duration: Optional[int] = None
    rating: Optional[float] = None
    language: Optional[list[str]] = Field(None, max_length=50)
    genres: Optional[list[str]] = Field(None, max_length=50)
    release_date: Optional[date] = None
    certificate: Optional[str] = Field(None, max_length=10)
    poster_url: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    cast: Optional[list[dict]] = None
    crew: Optional[list[dict]] = None

class MovieOut(MovieBase):
    movie_id: int