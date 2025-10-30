from __future__ import annotations

from datetime import datetime as dt
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Time,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from database import Base
#enum for show status
class ShowStatusEnum(str, Enum):
    UPCOMING = "UPCOMING"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
#screen
class Screen(Base):
    __tablename__="screens"
    screen_id=Column(Integer, primary_key=True, index=True)
    screen_name=Column(String(100), nullable=False)
    total_seats=Column(Integer, nullable=False)
    screen_type=Column(String(50), nullable=False)
    is_available=Column(Boolean, default=True)
  
    seats = relationship("Seat", back_populates="screen", cascade="all,delete-orphan")
    categories = relationship("SeatCategory", back_populates="screen", cascade="all,delete-orphan")
    shows = relationship("Show", back_populates="screen", cascade="all,delete-orphan")

#seat_category
class SeatCategory(Base):
    __tablename__="seat_categories"
    category_id=Column(Integer, primary_key=True, index=True)
    category_name=Column(String(100), nullable=False)
    screen_id=Column(Integer, ForeignKey("screens.screen_id"), nullable=False)
    rows=Column(Integer, nullable=False)
    cols=Column(Integer, nullable=False)
    base_price=Column(Float, nullable=False)

    screen = relationship("Screen", back_populates="categories")
    seats = relationship("Seat", back_populates="category", cascade="all,delete-orphan")

    

#show
class Show(Base):
    __tablename__ = "shows"

    show_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id", ondelete="CASCADE"), nullable=False)
    screen_id = Column(Integer, ForeignKey("screens.screen_id", ondelete="CASCADE"), nullable=False)
    show_date = Column(Date, nullable=False)
    show_time = Column(Time, nullable=False)  
    end_time = Column(Time, nullable=False)
    status = Column(SAEnum(ShowStatusEnum, name="show_status_enum"), nullable=False, server_default=ShowStatusEnum.UPCOMING.value)
    created_at = Column(DateTime(timezone=True), default=dt.utcnow, nullable=False)

    # Relations
    movie = relationship("Movie", back_populates="shows")
    screen = relationship("Screen", back_populates="shows")
    category_pricing = relationship("ShowCategoryPricing", back_populates="show", cascade="all,delete-orphan")

    __table_args__ = (
        Index("ix_shows_movie_id", "movie_id"),
        Index("ix_shows_screen_id", "screen_id"),
        Index("ix_shows_show_date", "show_date"), 
        UniqueConstraint("screen_id", "show_date", "show_time", name="uq_screen_date_time")
    )

#show_category_price
class ShowCategoryPricing(Base):
    __tablename__ = "show_category_pricing"

    pricing_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("shows.show_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("seat_categories.category_id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

    # Relations
    show = relationship("Show", back_populates="category_pricing")
    category = relationship("SeatCategory")

    __table_args__ = (
        UniqueConstraint("show_id", "category_id", name="uq_pricing_show_category"),
        Index("ix_pricing_show_id", "show_id"),
        Index("ix_pricing_category_id", "category_id"),
    )
