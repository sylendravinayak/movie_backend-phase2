from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from model.feedback import Feedback


def get_feedback(db: Session, feedback_id: int) -> Optional[Feedback]:
    return db.query(Feedback).filter(Feedback.feedback_id == feedback_id).first()


def list_feedbacks(db: Session, skip: int = 0, limit: int = 50) -> List[Feedback]:
    return (
        db.query(Feedback)
        .order_by(Feedback.feedback_date.desc(), Feedback.feedback_id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_feedback(db: Session, *, booking_id: int, user_id: int, rating: int, comment: Optional[str]) -> Feedback:
    fb = Feedback(
        booking_id=booking_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def update_feedback(db: Session, *, feedback_id: int, rating: Optional[int] = None, comment: Optional[str] = None) -> Optional[Feedback]:
    fb = get_feedback(db, feedback_id)
    if not fb:
        return None
    if rating is not None:
        fb.rating = rating
    if comment is not None:
        fb.comment = comment
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def delete_feedback(db: Session, *, feedback_id: int) -> bool:
    fb = get_feedback(db, feedback_id)
    if not fb:
        return False
    db.delete(fb)
    db.commit()
    return True


def set_reply(db: Session, *, feedback_id: int, reply: str) -> Optional[Feedback]:
    fb = get_feedback(db, feedback_id)
    if not fb:
        return None
    fb.reply = reply
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb