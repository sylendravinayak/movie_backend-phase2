from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, condecimal, conint
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
    payment_id: Optional[int] = Field(None)
    discount_id: Optional[int] = Field(None, description="FK to DISCOUNTS")
    booking_time: datetime =Field(default_factory=datetime.utcnow)
    amount: int=0
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
class DiscountBase(BaseModel):
    promo_code: str = Field(..., max_length=50)
    discount_type: Literal["percent", "flat"] = "percent"

    # For percent coupons
    discount_percent: Optional[int] = Field(
        None, description="Percentage value between 1 and 100 for percent-type discounts"
    )
    max_discount_amount: Optional[int] = Field(
        None, description="Optional cap for percent discounts (₹)"
    )

    # For flat coupons
    discount_amount: Optional[int] = Field(
        None, description="Flat amount in ₹ for flat-type discounts"
    )

    # Minimum cart value required (before taxes)
    min_subtotal: Optional[int  ] = Field(
        0, description="Minimum subtotal before GST required to apply the coupon (₹)"
    )

    # Validity window (optional)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    # Active toggle
    is_active: bool = True

    # Usage limit per user
    usage_limit_per_user: Optional[int] = Field(
        None, description="Max times a user can redeem this code"
    )

    # Optional scoping
    applicable_show_id: Optional[int] = Field(
        None, description="Limit coupon to a specific show ID"
    )
    applicable_movie_id: Optional[int] = Field(
        None, description="Limit coupon to a specific movie ID"
    )


class DiscountCreate(DiscountBase):
    """
    Schema for creating a Discount.
    Enforce logical constraints in your service layer:
    - If discount_type == 'percent' => discount_percent must be provided
    - If discount_type == 'flat'    => discount_amount must be provided
    """
    pass


class DiscountUpdate(BaseModel):
    """
    Partial update schema. All fields optional.
    """
    promo_code: Optional[str] = Field(None, max_length=50)
    discount_type: Optional[Literal["percent", "flat"]] = None

    discount_percent: Optional[int] = None
    max_discount_amount: Optional[int] = None
    discount_amount: Optional[int] = None

    min_subtotal: Optional[int] = None

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    is_active: Optional[bool] = None
    usage_limit_per_user: Optional[int] = None

    applicable_show_id: Optional[int] = None
    applicable_movie_id: Optional[int] = None


class DiscountOut(DiscountBase):
    discount_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # pydantic v2: allow ORM model -> schema


# Validation request/response for applying a coupon to a cart


