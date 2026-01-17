from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database import SessionLocal
from schemas.booking_schema import BookingCreate
from chatbot.state import ChatState

# Import the existing booking endpoint function so we reuse its full business logic.
# It is implemented in app/routers/booking_routes.create_booking (async).
from routers.booking_routes import create_booking as create_booking_endpoint  # type: ignore


def _get_db() -> Session:
    return SessionLocal()


async def confirm_booking(state: ChatState) -> ChatState:
    """
    Confirm node: reuse existing booking endpoint logic rather than re-implementing.
    This ensures seat/lock validation, GST, foods, notifications, and DB transactions
    are handled by the system's trusted code path.
    """
    # If still awaiting user input, keep waiting
    if state.get("awaiting_user"):
        return state

    user_id = state.get("user_id")
    show_id = state.get("show_id")
    seat_ids = state.get("seat_ids") or []
    if not (user_id and show_id and seat_ids):
        state["awaiting_user"] = True
        state["response"] = "I still need seats to confirm. Please provide seat numbers."
        state["missing_fields"] = ["seat_ids"]
        state["next_node"] = "seat"
        return state

    db = _get_db()
    try:
        # Build BookingCreate payload consistent with API expectations.
        booking_in = BookingCreate(
            user_id=int(user_id),
            show_id=int(show_id),
            seats=[int(s) for s in seat_ids],
            foods=[],
            discount_id=None,
            payment_id=None,
        )

        # The router function expects (obj: BookingCreate, db: Session, payload: dict)
        # We pass an empty payload dict; create_booking reads user_id from booking_in.
        booking = await create_booking_endpoint(booking_in, db, payload={})

        # create_booking_endpoint returns the Booking ORM object on success
        # (same behaviour as POST /bookings/). Extract reference and id if present.
        if getattr(booking, "booking_id", None):
            state["booking_id"] = booking.booking_id
            state["booking_reference"] = getattr(booking, "booking_reference", None)
            state["response"] = f"Booking confirmed! Ref: {state['booking_reference']}. Enjoy your show."
            state["awaiting_user"] = False
            state["missing_fields"] = []
            state["next_node"] = None
            return state

        # If booking endpoint returned something else (e.g., dict), try to be forgiving
        if isinstance(booking, dict) and booking.get("booking_id"):
            state["booking_id"] = booking.get("booking_id")
            state["booking_reference"] = booking.get("booking_reference")
            state["response"] = f"Booking confirmed! Ref: {state['booking_reference']}. Enjoy your show."
            state["awaiting_user"] = False
            state["missing_fields"] = []
            state["next_node"] = None
            return state

        # Unknown return type
        state["response"] = "Booking endpoint returned unexpected result."
        state["awaiting_user"] = False
        return state

    except HTTPException as e:
        # Forward HTTP exception details to the user
        state["response"] = f"Failed to book: {e.detail}"
        state["awaiting_user"] = False
        return state
    except Exception as e:  # pragma: no cover
        # Defensive: log and surface a user-facing error without leaking internals
        state["response"] = f"Unexpected error while booking: {str(e)}"
        state["awaiting_user"] = False
        return state
    finally:
        db.close()