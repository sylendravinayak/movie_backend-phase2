from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func,
)
from database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("bookings.booking_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    feedback_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reply = Column(String(1000), nullable=True, default=None)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="feedback_rating_between_1_5"),
    )