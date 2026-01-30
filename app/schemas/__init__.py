from __future__ import annotations

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


# Shared Pydantic base with ORM support (Pydantic v2)
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Value objects shared by multiple schemas
class CastMember(ORMModel):
    name: str = Field(..., max_length=100)
    character_name: str = Field(..., max_length=100)


class CrewMember(ORMModel):
    name: str = Field(..., max_length=100)
    role: str = Field(..., max_length=100)


# Enums shared across schemas
class ScreenType(str, Enum):
    STANDARD = "STANDARD"
    IMAX = "IMAX"
    DX4 = "4DX"


class ShowStatus(str, Enum):
    UPCOMING = "UPCOMING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class SeatLockStatus(str, Enum):
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"
    EXPIRED = "EXPIRED"


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    WALLET = "WALLET"


class BackupType(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"


class BackupStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RestoreStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"




class MovieDisplayConstraint(BaseModel):
    movie: str
    min_shows_per_day: Optional[int] = None
    max_shows_per_day: Optional[int] = None
    min_shows_per_week: Optional[int] = None
    max_shows_per_week: Optional[int] = None
    prime_show_quota: Optional[int] = None


class AgentRequest(BaseModel):

    intent: str = Field(
        description="forecast, scheduling, pricing, optimize, reschedule, cancel"
    )

    show_id: Optional[int] = None

    movies: Optional[List[str]] = None

    display_constraints: Optional[List[MovieDisplayConstraint]] = None

    forecast_days: Optional[int] = Field(14, description="Number of days to forecast")