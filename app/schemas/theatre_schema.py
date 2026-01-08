from __future__ import annotations

from datetime import date, time, datetime
from typing import Optional

from pydantic import Field

from . import ORMModel, ScreenType, ShowStatus


# 3. SCREEN
class ScreenBase(ORMModel):
    screen_name: str = Field(..., max_length=50)
    screen_type: str =Field(..., max_length=50)
    is_available: bool = True


class ScreenCreate(ScreenBase):
    pass


class ScreenUpdate(ORMModel):
    screen_name: Optional[str] = Field(None, max_length=50)
    screen_type: Optional[str] = None
    is_available: Optional[bool] = None


class ScreenOut(ScreenBase):
    screen_id: int


# 4. SEAT_CATEGORY
class SeatCategoryBase(ORMModel):
    category_name: str = Field(..., max_length=50)
    screen_id: int
    rows: int = Field(..., ge=1)
    cols: int = Field(..., ge=1)
    base_price: float = Field(..., ge=0, le=999.99)


class SeatCategoryCreate(SeatCategoryBase):
    pass


class SeatCategoryUpdate(ORMModel):
    category_name: Optional[str] = Field(None, max_length=50)
    screen_id: Optional[int] = None
    rows: Optional[int] = Field(None, ge=1)
    cols: Optional[int] = Field(None, ge=1)
    base_price: Optional[float] = Field(None, ge=0, le=999.99)


class SeatCategoryOut(SeatCategoryBase):
    category_id: int


# 7. SHOW
class ShowBase(ORMModel):
    movie_id: int
    screen_id: int
    show_date: date
    show_time: time
    status: ShowStatus = ShowStatus.UPCOMING
    format: Optional[str] = Field("2D", description="List of formats, e.g., 2D, 3D, IMAX")
    language: Optional[str] = Field("Tamil", description="List of languages")


class ShowCreate(ShowBase):
    pass


class ShowUpdate(ORMModel):
    movie_id: Optional[int] = None
    screen_id: Optional[int] = None
    show_date: Optional[date] = None
    show_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[ShowStatus] = None


class ShowOut(ShowBase):
    show_id: int
    created_at: datetime


# 8. SHOW_CATEGORY_PRICING
class ShowCategoryPricingBase(ORMModel):
    show_id: int
    category_id: int
    price: Optional[float] = Field(..., ge=0, le=999.99)


class ShowCategoryPricingCreate(ShowCategoryPricingBase):
    pass


class ShowCategoryPricingUpdate(ORMModel):
    price: Optional[float] = Field(None, ge=0, le=999.99)


class ShowCategoryPricingOut(ShowCategoryPricingBase):
    pricing_id: int