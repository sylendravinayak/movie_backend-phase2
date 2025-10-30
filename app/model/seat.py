from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index,Enum as SAEnum,DateTime,Boolean
from sqlalchemy.orm import relationship
from database import Base
from enum import Enum
from sqlalchemy.sql import func
#seat
class Seat(Base):
    __tablename__ = "seats"

    seat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    screen_id = Column(Integer, ForeignKey("screens.screen_id", ondelete="CASCADE"), nullable=False)
    row_number = Column(Integer, nullable=False)
    col_number = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("seat_categories.category_id", ondelete="SET NULL"), nullable=True)
    seat_number = Column(String(10), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)  # 1 for available, 0 for unavailable
    # Relations
    screen = relationship("Screen", back_populates="seats")
    category = relationship("SeatCategory", back_populates="seats")

    __table_args__ = (
        UniqueConstraint("screen_id", "seat_number", name="uq_seat_screen_seatnum"),
        Index("ix_seats_screen_id", "screen_id"),
        Index("ix_seats_category_id", "category_id"),
    )
#seat_lock
class SeatLockStatusEnum(str, Enum):
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"


# ---------------------------------------------------------------------------
# 6. SEAT_LOCK
# Note: seat_id and show_id point to external services; kept as plain ints to avoid cross-DB FKs.
# ---------------------------------------------------------------------------

class SeatLock(Base):
    __tablename__ = "seat_locks"

    lock_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    seat_id = Column(Integer, ForeignKey("seats.seat_id", ondelete="CASCADE"), nullable=False)
    show_id = Column(Integer, ForeignKey("shows.show_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(SeatLockStatusEnum, name="seat_lock_status_enum"), nullable=False, server_default=SeatLockStatusEnum.LOCKED.value)
    locked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_seat_locks_seat_show", "seat_id", "show_id"),
        Index("ix_seat_locks_expires_at", "expires_at"),
    )