from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Index,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base  


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BookingStatusEnum(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class StatusChangedByEnum(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"
    PAYMENT_SERVICE = "PAYMENT_SERVICE"


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)   # users.user_id (external)
    show_id = Column(Integer, nullable=False, index=True)   # shows.show_id (external)
    booking_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    booking_reference = Column(String(20), nullable=False, unique=True, index=True)
    booking_status = Column(SAEnum(BookingStatusEnum, name="booking_status_enum"), nullable=False, server_default=BookingStatusEnum.PENDING.value)
    payment_id = Column(Integer, nullable=True, index=True)   # payments.payment_id (external)
    discount_id = Column(Integer, nullable=True, index=True)  # discounts.discount_id (external)
    booking_time = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Integer)

    # Relations
    seats = relationship("BookedSeat", back_populates="booking", cascade="all,delete-orphan")
    foods = relationship("BookedFood", back_populates="booking", cascade="all,delete-orphan")
    status_logs = relationship("BookingStatusLog", back_populates="booking", cascade="all,delete-orphan")


# ---------------------------------------------------------------------------
# 11. BOOKED_SEAT
# ---------------------------------------------------------------------------

class BookedSeat(Base):
    __tablename__ = "booked_seats"

    booked_seat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    seat_id = Column(Integer, nullable=False, index=True)    # seats.seat_id (external)
    price = Column(Numeric(10, 2), nullable=False)
    show_id = Column(Integer, nullable=False, index=True)    # shows.show_id (external)
    gst_id = Column(Integer, nullable=True, index=True)      # gst.gst_id (external)

    booking = relationship("Booking", back_populates="seats")

    __table_args__ = (
        UniqueConstraint("booking_id", "seat_id", name="uq_booked_seat_booking_seat"),
        UniqueConstraint("seat_id", "show_id", name="uq_booked_seat_seat_show"),
        Index("ix_booked_seats_booking_id", "booking_id"),
    )


# ---------------------------------------------------------------------------
# 14. BOOKED_FOOD
# ---------------------------------------------------------------------------

class BookedFood(Base):
    __tablename__ = "booked_food"

    booked_food_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    food_id = Column(Integer, nullable=False, index=True)    # food_items.food_id (external)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    gst_id = Column(Integer, nullable=True, index=True)      # gst.gst_id (external)

    booking = relationship("Booking", back_populates="foods")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_booked_food_quantity_gt_0"),
        Index("ix_booked_food_booking_id", "booking_id"),
    )


# ---------------------------------------------------------------------------
# booking_status (history/log)
# ---------------------------------------------------------------------------

class BookingStatusLog(Base):
    __tablename__ = "booking_status"

    status_log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    from_status = Column(SAEnum(BookingStatusEnum, name="booking_status_enum"), nullable=True)
    to_status = Column(SAEnum(BookingStatusEnum, name="booking_status_enum"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    changed_by = Column(SAEnum(StatusChangedByEnum, name="status_changed_by_enum"), nullable=True)
    reason = Column(Text, nullable=True)

    booking = relationship("Booking", back_populates="status_logs")

    __table_args__ = (
        Index("ix_booking_status_booking_id", "booking_id"),
        Index("ix_booking_status_changed_at", "changed_at"),
    )

class GST(Base):
    __tablename__ = "gst"

    gst_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    s_gst = Column(Integer, nullable=False)
    c_gst = Column(Integer, nullable=False)
    gst_category = Column(String(100), nullable=False)

    __table_args__ = (
        Index("ix_gst_category", "gst_category"),
    )    

class Discount(Base):
    __tablename__ = "discounts"

    discount_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    promo_code = Column(String(50), nullable=False, unique=True)
    discount_percent = Column(Integer, nullable=False)
