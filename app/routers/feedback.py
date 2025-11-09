from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from crud import feedback as feedback_crud
from schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackReply,
    FeedbackOut,
)
from utils.auth.jwt_bearer import JWTBearer,getcurrent_user
from schemas import UserRole
# Adjust this import if your EmailService file/module name differs
from utils.email_servicer import EmailService

# If you have a user model for email lookup
try:
    from model.user import User  # expected: user_id, email, and optionally full_name/name/username
except Exception:  # pragma: no cover - soft import in case of different path
    User = None  # type: ignore

router = APIRouter(prefix="/feedbacks", tags=["Feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))) -> FeedbackOut:
    fb = feedback_crud.create_feedback(
        db,
        booking_id=payload.booking_id,
        user_id=payload.user_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return fb  # FastAPI will convert via orm_mode


@router.get("", response_model=List[FeedbackOut])
def list_feedbacks(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))) -> List[FeedbackOut]:
    return feedback_crud.list_feedbacks(db, skip=skip, limit=limit)


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: int, db: Session = Depends(get_db), payload: dict = Depends(JWTBearer())) -> FeedbackOut:
    fb = feedback_crud.get_feedback(db, feedback_id)
    if not fb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return fb



@router.post("/{feedback_id}/reply", response_model=FeedbackOut)
async def reply_to_feedback(feedback_id: int, payload: FeedbackReply, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))) -> FeedbackOut:
    # 1) Persist the admin reply
    fb = feedback_crud.set_reply(db, feedback_id=feedback_id, reply=payload.reply)
    if not fb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    # 2) Resolve user email and name for notification
    to_email: Optional[str] = None
    user_name: Optional[str] = None

    if User is not None:
        user = db.query(User).filter(getattr(User, "user_id") == fb.user_id).first()
        if user:
            to_email = getattr(user, "email", None)
            user_name = (
                getattr(user, "full_name", None)
                or getattr(user, "name", None)
                or getattr(user, "username", None)
                or (to_email.split("@")[0] if to_email else None)
            )

    # 3) Send email if we have a user email
    if to_email:
        email_service = EmailService()

        # Prefer using your existing notification.html template
        # with a "feedback_reply" type and appropriate metadata.
        html = email_service.render(
            "notification.html",
            dict(
                user_name=user_name or "there",
                type="feedback_reply",
                title="Reply to your feedback",
                message="Our team has replied to your feedback.",
                metadata={
                    "feedbackId": fb.feedback_id,
                    "bookingId": fb.booking_id,
                    "rating": fb.rating,
                    "comment": fb.comment,
                    "reply": fb.reply,
                },
                # Frontend URL picked up by your template through Settings
                frontend_url=None,
                deeplink=None,
            ),
        )
        subject = f"📩 Reply to your feedback (Booking #{fb.booking_id})"
        await email_service.send_email(to_email=to_email, subject=subject, html_content=html)

    # Return the updated feedback
    return fb