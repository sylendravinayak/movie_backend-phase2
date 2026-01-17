from __future__ import annotations

import os
import logging
from typing import List, Optional, Dict, Any
import asyncio
import httpx

from chatbot.state import ChatState
from database import SessionLocal
from model import Booking, Show, Movie
from sqlalchemy.orm import Session

logger = logging.getLogger("chat_graph.cancel_http")
logger.setLevel(logging.DEBUG)

CANCEL_API_BASE = os.getenv("CANCEL_API_BASE", "http://localhost:8000")
CANCEL_TIMEOUT_SECONDS = float(os.getenv("CANCEL_TIMEOUT_SECONDS", "10.0"))


def _get_db() -> Session:
    return SessionLocal()


def _format_booking_option(b: Booking, show: Optional[Show], movie: Optional[Movie]) -> str:
    show_str = ""
    if show:
        time_str = getattr(show, "show_time", None)
        date_str = getattr(show, "show_date", None)
        if date_str and time_str:
            try:
                time_s = time_str.strftime("%H:%M")
            except Exception:
                time_s = str(time_str)
            show_str = f"{date_str} {time_s}"
    movie_title = movie.title if movie else getattr(b, "movie_title", "movie")
    return f"{b.booking_id} — {movie_title} at {show_str} ({b.booking_status})"


def _extract_jwt_from_state(state: ChatState) -> Optional[str]:
    """
    Look for a JWT in common state keys. Adapt this to your app's authentication state shape.
    """
    # Common keys to check
    candidates = [
        "auth_token",
        "jwt",
        "jwt_token",
        "authorization",  # might contain "Bearer <token>"
        "access_token",
        "token",
        "payload",  # might be a dict with tokens
    ]
    for k in candidates:
        v = state.get(k)
        if not v:
            continue
        # If header-like "Bearer <token>" return token part
        if isinstance(v, str) and v.strip().lower().startswith("bearer "):
            return v.strip().split(None, 1)[1]
        if isinstance(v, str):
            # assume raw token string
            return v.strip()
        if isinstance(v, dict):
            # common field names inside payload
            for sub in ("access_token", "token", "jwt", "id_token"):
                if sub in v and isinstance(v[sub], str):
                    return v[sub]
    # also check nested payload if present
    payload = state.get("payload")
    if isinstance(payload, dict):
        for sub in ("access_token", "token", "jwt", "id_token"):
            if sub in payload and isinstance(payload[sub], str):
                return payload[sub]
    return None


async def _call_cancel_endpoint_with_jwt(booking_id: int, user_jwt: str, timeout: float = CANCEL_TIMEOUT_SECONDS) -> Dict[str, Any]:
    url = f"{CANCEL_API_BASE.rstrip('/')}/bookings/cancel/{booking_id}"
    headers = {"Authorization": f"Bearer {user_jwt}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.put(url, headers=headers)
        try:
            data = resp.json()
        except Exception:
            data = {"status_code": resp.status_code, "text": resp.text}
        return {"status_code": resp.status_code, "data": data}


async def handle_cancel_via_http(state: ChatState) -> ChatState:
    # Respect node interrupt semantics
    if state.get("awaiting_user"):
        if state.get("next_node") not in ("cancel", "cancel_confirm"):
            return state

    user_id = state.get("user_id")
    if not user_id:
        state["awaiting_user"] = True
        state["response"] = "I need you to sign in before I can cancel a booking. Please sign in."
        state["missing_fields"] = ["user_id"]
        state["next_node"] = "cancel"
        return state

    # If booking_id present but no confirmation yet -> ask for confirmation
    booking_id = state.get("booking_id")
    if booking_id and state.get("next_node") != "cancel_confirm":
        state["awaiting_user"] = True
        state["next_node"] = "cancel_confirm"
        state["missing_fields"] = ["cancel_confirm"]
        state["response"] = f"Please confirm: cancel booking {booking_id}? Reply 'yes' to confirm or 'no' to abort."
        return state

    # If confirmation step
    if state.get("next_node") == "cancel_confirm":
        msg = (state.get("message") or "").strip().lower()
        if msg in ("yes", "y", "confirm"):
            # Extract JWT from state and fail fast if missing
            user_jwt = _extract_jwt_from_state(state)
            if not user_jwt:
                state["awaiting_user"] = True
                state["next_node"] = "auth"
                state["missing_fields"] = ["auth_token"]
                state["response"] = "I need you to sign in before I can cancel your booking. Please sign in."
                return state

            try:
                result = await _call_cancel_endpoint_with_jwt(int(booking_id), user_jwt)
            except Exception as e:
                logger.exception("HTTP cancel endpoint call failed: %s", e)
                state["awaiting_user"] = False
                state["next_node"] = None
                state["response"] = "Sorry, I couldn't reach the booking service to cancel right now. Please try again later."
                return state

            status_code = result.get("status_code")
            payload = result.get("data") or {}
            if status_code in (200, 201):
                refund_amount = payload.get("refund_amount", payload.get("refund_amount_cents", 0))
                # Try to normalize cents -> display amount if we detect cents (heuristic)
                display = str(refund_amount)
                if isinstance(refund_amount, int) and refund_amount > 1000:
                    display = f"{refund_amount/100:.2f}"
                state["awaiting_user"] = False
                state["next_node"] = None
                state["response"] = f"Booking {booking_id} cancelled. Refund status: {payload.get('refund_status','unknown')}. Refund amount: {display}."
                state["booking_cancel_result"] = payload
                return state
            else:
                err_msg = payload.get("detail") or payload.get("message") or str(payload)
                state["awaiting_user"] = False
                state["next_node"] = None
                state["response"] = f"Could not cancel booking: {err_msg}"
                logger.debug("Cancel endpoint returned %s: %s", status_code, payload)
                return state

        elif msg in ("no", "n", "abort", "cancel"):
            state["awaiting_user"] = False
            state["next_node"] = None
            state["missing_fields"] = []
            state["response"] = "Okay — I won't cancel your booking. Anything else I can help with?"
            return state
        else:
            state["awaiting_user"] = True
            state["next_node"] = "cancel_confirm"
            state["response"] = "Please reply 'yes' to confirm cancellation or 'no' to keep your booking."
            return state

    # If we reach here we need to list user's recent bookings to pick from
    db = _get_db()
    try:
        rows: List[Booking] = (
            db.query(Booking)
            .filter(Booking.user_id == user_id)
            .order_by(Booking.booking_id.desc())
            .limit(8)
            .all()
        )
        if not rows:
            state["awaiting_user"] = False
            state["next_node"] = None
            state["response"] = "I couldn't find any recent bookings on your account. If you have a booking id, type it and I'll cancel it."
            state["missing_fields"] = ["booking_id"]
            return state

        options: List[Dict[str, Any]] = []
        for idx, b in enumerate(rows, start=1):
            show = None
            movie = None
            try:
                if getattr(b, "show_id", None):
                    show = db.query(Show).filter(Show.show_id == b.show_id).first()
                    if show and getattr(show, "movie_id", None):
                        movie = db.query(Movie).filter(Movie.movie_id == show.movie_id).first()
            except Exception:
                pass
            label = _format_booking_option(b, show, movie)
            options.append({"index": idx, "booking_id": b.booking_id, "label": label})

        state["cancel_options"] = options
        labels = "\n".join([f"{o['index']}. {o['label']}" for o in options])
        state["awaiting_user"] = True
        state["next_node"] = "cancel"
        state["missing_fields"] = ["booking_id"]
        state["response"] = "Which booking would you like to cancel? Reply with the option number or booking id:\n" + labels
        return state
    finally:
        db.close()