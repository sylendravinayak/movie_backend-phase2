from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime,JSON,ARRAY
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Movie(Base):
    __tablename__="movies"
    movie_id=Column(Integer, primary_key=True, index=True)
    title=Column(String(200), nullable=False)
    description=Column(String(1000), nullable=True)
    duration=Column(Integer, nullable=False)  # in minutes
    genre=Column(ARRAY(String(50)), nullable=True)
    format=Column(ARRAY(String(50)), nullable=True)  # e.g., 2D, 3D, IMAX
    language=Column(ARRAY(String(50)), nullable=True)
    release_date=Column(DateTime, nullable=True)
    rating=Column(Float, nullable=True)  # e.g., 4.5 out of 5.0
    certificate=Column(String(10), nullable=True)
    poster_url=Column(String(255), nullable=True)
    background_image_url=Column(String(255), nullable=True)
    is_active=Column(Boolean, default=True)
    cast=Column(JSON, nullable=True)  # JSON string
    crew=Column(JSON, nullable=True)  # JSON string
    imdb_id=Column(String(20), nullable=True)

    shows = relationship("Show", back_populates="movie", cascade="all,delete-orphan")