from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON


# ---------------------------------------------------------------------------
# Shared base (Pydantic v2 ORM mode)
# ---------------------------------------------------------------------------

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class StatusChangedBy(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"
    PAYMENT_SERVICE = "PAYMENT_SERVICE"


# ---------------------------------------------------------------------------
# bookings
# ---------------------------------------------------------------------------

class BookingBase(ORMModel):
    user_id: int
    show_id: int
    booking_reference: str = Field(..., max_length=20)
    booking_status: BookingStatus = BookingStatus.PENDING
    payment_id: Optional[int] = Field(None, description="FK to PAYMENT")
    discount_id: Optional[int] = Field(None, description="FK to DISCOUNTS")
    booking_time: datetime
    amount: int  # total amount for booking (currency as integer minor units or whole units)
    seats: Optional[list[int]] = Field(default_factory=list, description="List of seat IDs booked")
    foods: Optional[list[dict]] = Field(default_factory=list, description="List of food IDs ordered")


class BookingCreate(BookingBase):
    pass


class BookingUpdate(ORMModel):
    booking_status: Optional[BookingStatus] | None = None
    payment_id: Optional[int] | None = None
    discount_id: Optional[int] = None
    amount: Optional[int] = None


class BookingOut(ORMModel):
    booking_id: int
    user_id: int
    show_id: int
    booking_reference: str
    booking_status: BookingStatus
    payment_id: Optional[int] = None
    discount_id: Optional[int] = None
    booking_time: datetime
    amount: int
    seats: Optional[list[BookedSeatOut]] = None
    foods: Optional[list[BookedFoodOut]] = None


# ---------------------------------------------------------------------------
# booking_seats
# ---------------------------------------------------------------------------

class BookedSeatBase(ORMModel):
    booking_id: int
    seat_id: int
    show_id: int
    price: float
    gst_id: Optional[int] = Field(None, description="FK to GST")


class BookedSeatCreate(BookedSeatBase):
    pass


class BookedSeatUpdate(ORMModel):
    price: Optional[float] = None
    gst_id: Optional[int] = None


class BookedSeatOut(BookedSeatBase):
    booked_seat_id: int


# ---------------------------------------------------------------------------
# booking_food
# ---------------------------------------------------------------------------

class BookedFoodBase(ORMModel):
    booking_id: int
    food_id: int
    quantity: int
    unit_price: float
    gst_id: Optional[int] = Field(None, description="FK to GST")


class BookedFoodCreate(BookedFoodBase):
    pass


class BookedFoodUpdate(ORMModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    gst_id: Optional[int] = None


class BookedFoodOut(BookedFoodBase):
    booked_food_id: int

#gst


class GSTBase(ORMModel):
    s_gst: int
    c_gst: int
    gst_category: str = Field(..., max_length=100)


class GSTCreate(GSTBase):
    pass


class GSTUpdate(ORMModel):
    s_gst: Optional[int] = None
    c_gst: Optional[int] = None
    gst_category: Optional[str] = Field(None, max_length=100)


class GSTOut(GSTBase):
    gst_id: int

#discount

class DiscountBase(ORMModel):
    promo_code: str
    discount_percent: int

class DiscountCreate(DiscountBase):
    pass

class DiscountUpdate(ORMModel):
    promo_code: str | None = None
    discount_percent: int | None = None

class DiscountResponse(DiscountBase):
    discount_id: int