from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from model import Show
from chatbot.state import ChatState


def _get_db() -> Session:
    return SessionLocal()


async def resolve_showtime(state: ChatState) -> ChatState:
    if state.get("awaiting_user"):
        return state
    if state.get("show_id"):
        return state

    screen_id = state.get("screen_id")
    movie_id = state.get("movie_id")
    show_date = state.get("show_date")
    show_time = state.get("show_time")

    if not (screen_id and movie_id and show_date):
        state["awaiting_user"] = True
        state["response"] = "I need screen, movie, and date to pick a showtime."
        state["missing_fields"] = [f for f in ["screen_id", "movie_id", "show_date"] if not state.get(f)]
        state["next_node"] = "showtime"
        return state

    db = _get_db()
    try:
        query = (
            db.query(Show)
            .filter(
                Show.screen_id == screen_id,
                Show.movie_id == movie_id,
                Show.show_date == show_date,
            )
            .order_by(Show.show_time)
            .all()
        )

        if not query:
            state["awaiting_user"] = True
            state["response"] = "No shows found for that screen/date. Want a different time or screen?"
            state["missing_fields"] = ["show_time"]
            state["next_node"] = "showtime"
            return state

        if show_time:
            match = next((s for s in query if s.show_time == show_time), None)
            if match:
                state["show_id"] = match.show_id
                return state

        if len(query) == 1:
            state["show_id"] = query[0].show_id
            state["show_time"] = query[0].show_time
            return state

        # ask user to choose
        options = ", ".join([s.show_time.strftime("%H:%M") for s in query])
        state["awaiting_user"] = True
        state["response"] = f"Available times are: {options}. Which time should I book?"
        state["missing_fields"] = ["show_time"]
        state["next_node"] = "showtime"
        return state
    finally:
        db.close()