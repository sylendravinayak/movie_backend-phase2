from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field




class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"




class NotificationBase(ORMModel):
    user_id: int
    booking_id: Optional[int] = Field(None, description="Related booking (if applicable)")
    notification_type: str = Field(..., max_length=50, description="Type of notification")
    message: str
    is_read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(ORMModel):
    notification_type: Optional[str] = Field(None, max_length=50)
    message: Optional[str] = None
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class NotificationOut(NotificationBase):
    notification_id: str = Field(..., description="Mongo ObjectId as string")
    created_at: datetime
    read_at: Optional[datetime] = None

