from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel,Field


class FeedbackBase(BaseModel):
    booking_id: int
    user_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None


class FeedbackReply(BaseModel):
    reply: str


class FeedbackOut(FeedbackBase):
    feedback_id: int
    feedback_date: datetime
    reply: Optional[str] = None

    class Config:
        orm_mode = True