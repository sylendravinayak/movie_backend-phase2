from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from . import ORMModel, SeatLockStatus


# 5. SEAT
class SeatBase(ORMModel):
    screen_id: int
    row_number: int
    col_number: int
    category_id: int
    seat_number: Optional[str] = Field(None, max_length=10, description="e.g., A1, B5")
    is_available: bool = True


class SeatCreate(SeatBase):
    pass


class SeatUpdate(ORMModel):
    screen_id: Optional[int] = None
    row_number: Optional[int] = None
    col_number: Optional[int] = None
    category_id: Optional[int] = None
    seat_number: Optional[str] = Field(None, max_length=10)
    is_available: bool = True


class SeatOut(SeatBase):
    seat_id: int


# 6. SEAT_LOCK
class SeatLockBase(ORMModel):
    seat_id: int
    show_id: int
    user_id: int = Field(..., description="User who locked the seat (UUID)")
    status: SeatLockStatus = SeatLockStatus.LOCKED
    locked_at: Optional[datetime] = None
    expires_at: datetime


class SeatLockCreate(SeatLockBase):
    pass


class SeatLockUpdate(ORMModel):
    status: Optional[SeatLockStatus] = None
    expires_at: Optional[datetime] = None


class SeatLockOut(SeatLockBase):
    lock_id: int