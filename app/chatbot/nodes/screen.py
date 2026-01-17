from __future__ import annotations

import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, not_, select
from database import SessionLocal
from model import Show, Screen, Movie, Seat, BookedSeat
from model.seat import SeatLock,SeatLockStatusEnum
from chatbot.state import ChatState
from datetime import datetime, timezone

logger = logging.getLogger("chat_graph.screen")
logger.setLevel(logging.DEBUG)


def _get_db() -> Session:
    return SessionLocal()


def _build_movie_options_from_rows(rows: List) -> List[Dict]:
    opts = []
    for idx, r in enumerate(rows, start=1):
        opts.append({"index": idx, "movie_id": r.movie_id, "title": r.title})
    return opts


def _match_text_against_options(text: str, options: List[Dict], key: str) -> List[Dict]:
    if not text or not options:
        return []
    norm = text.strip().lower()
    exact = [o for o in options if (o.get(key) or "").strip().lower() == norm]
    if exact:
        return exact
    return [o for o in options if norm in (o.get(key) or "").strip().lower()]


async def resolve_screen(state: ChatState) -> ChatState:
    """
    Enhanced screen node:
    - When movie_title/movie_id and show_date present but show_time/show_id missing,
      list available shows for that movie+date as `show_options`.
    - Accept selection by index or textual match (time or screen name) and set show_id/show_time/screen_id.
    - Otherwise, fallback to movie listing behavior.
    """
    # Respect earlier interrupts — allow processing if this node paused the flow or options exist.
    if state.get("awaiting_user"):
        if not (state.get("next_node") == "screen" or state.get("movie_options") or state.get("show_options")):
            return state

    db = _get_db()
    try:
        user_msg = (state.get("message") or "").strip()
        movie_title = state.get("movie_title")
        movie_id = state.get("movie_id")
        show_date = state.get("show_date")
        show_time = state.get("show_time")

        logger.debug(
            "SCREEN ENTER message=%r next_node=%r awaiting_user=%r movie_id=%r show_date=%r",
            user_msg,
            state.get("next_node"),
            state.get("awaiting_user"),
            movie_id,
            show_date,
        )

        # If we have movie_options and user selects, handle that first (existing behavior)
        movie_options = state.get("movie_options") or []
        if movie_options and user_msg and not movie_title and not movie_id:
            # numeric selection
            try:
                sel = int(user_msg)
                chosen = next((o for o in movie_options if o["index"] == sel), None)
                if chosen:
                    state["movie_title"] = chosen["title"]
                    state["movie_id"] = chosen["movie_id"]
                    state.pop("movie_options", None)
                # continue
            except Exception:
                matches = _match_text_against_options(user_msg, movie_options, "title")
                if len(matches) == 1:
                    state["movie_title"] = matches[0]["title"]
                    state["movie_id"] = matches[0]["movie_id"]
                    state.pop("movie_options", None)
                elif len(matches) > 1:
                    state["awaiting_user"] = True
                    state["missing_fields"] = ["movie_title"]
                    state["next_node"] = "screen"
                    state["movie_options"] = matches
                    state["response"] = "I found multiple movies that match. Please choose one:\n" + "\n".join([f"{o['index']}. {o['title']}" for o in matches])
                    return state

        # If movie identified by title text but not movie_id, try to resolve
        if not movie_id and movie_title:
            m = db.query(Movie).filter(Movie.title.ilike(f"%{movie_title}%")).first()
            if m:
                state["movie_id"] = m.movie_id
                movie_id = m.movie_id

        # If we have movie_id and show_date but no show_time/show_id -> present show options
        if movie_id and show_date and not state.get("show_id") and not show_time:
            # If user already has show_options and attempted selection, respect that mapping
            show_options = state.get("show_options") or []

            # If user sent a selection and show_options present, map selection first
            if show_options and user_msg:
                try:
                    sel = int(user_msg)
                    chosen = next((o for o in show_options if o["index"] == sel), None)
                    if chosen:
                        state["show_id"] = chosen["show_id"]
                        state["show_time"] = chosen["show_time"]
                        state["screen_id"] = chosen.get("screen_id")
                        state.pop("show_options", None)
                        # continue processing after selection
                    else:
                        # Try textual matching on time or screen_name
                        t_matches = _match_text_against_options(user_msg, show_options, "show_time")
                        s_matches = _match_text_against_options(user_msg, show_options, "screen_name")
                        combined = t_matches + [m for m in s_matches if m not in t_matches]
                        if len(combined) == 1:
                            chosen = combined[0]
                            state["show_id"] = chosen["show_id"]
                            state["show_time"] = chosen["show_time"]
                            state["screen_id"] = chosen.get("screen_id")
                            state.pop("show_options", None)
                        elif len(combined) > 1:
                            state["awaiting_user"] = True
                            state["missing_fields"] = ["show_id"]
                            state["next_node"] = "screen"
                            state["show_options"] = combined
                            state["response"] = "I found multiple shows that match. Please choose one:\n" + "\n".join([f"{o['index']}. {o['show_time']} at {o['screen_name']}" for o in combined])
                            return state
                except Exception:
                    # not an integer; attempt textual matching similar to above
                    t_matches = _match_text_against_options(user_msg, show_options, "show_time")
                    s_matches = _match_text_against_options(user_msg, show_options, "screen_name")
                    combined = t_matches + [m for m in s_matches if m not in t_matches]
                    if len(combined) == 1:
                        chosen = combined[0]
                        state["show_id"] = chosen["show_id"]
                        state["show_time"] = chosen["show_time"]
                        state["screen_id"] = chosen.get("screen_id")
                        state.pop("show_options", None)
                    elif len(combined) > 1:
                        state["awaiting_user"] = True
                        state["missing_fields"] = ["show_id"]
                        state["next_node"] = "screen"
                        state["show_options"] = combined
                        state["response"] = "I found multiple shows that match. Please choose one:\n" + "\n".join([f"{o['index']}. {o['show_time']} at {o['screen_name']}" for o in combined])
                        return state
                    # else fallthrough to presenting or re-presenting options below

            # Query shows for movie_id + show_date
            shows = (
                db.query(Show, Screen)
                .join(Screen, Screen.screen_id == Show.screen_id)
                .filter(Show.movie_id == movie_id, Show.show_date == show_date)
                .order_by(Show.show_time.asc())
                .all()
            )

            # Build show options with available seat count per show
            options: List[Dict] = []
            for idx, (show, screen) in enumerate(shows, start=1):
                # Calculate available seats count: seats on the screen that are available and not booked/locked for this show
                # Count seats for the show.screen_id with Seat.is_available True and not in booked/locked for this show
                booked_subq = db.query(BookedSeat.seat_id).filter(BookedSeat.show_id == show.show_id).subquery()
                locked_subq = (
                    db.query(SeatLock.seat_id)
                    .filter(
                        SeatLock.show_id == show.show_id,
                        SeatLock.status == SeatLockStatusEnum.LOCKED,
                        SeatLock.expires_at > datetime.now(timezone.utc),
                    )
                    .subquery()
                )
                available_count = (
                    db.query(func.count(Seat.seat_id))
                    .filter(Seat.screen_id == screen.screen_id, Seat.is_available == True)
                    .filter(not_(Seat.seat_id.in_(booked_subq)))
                    .filter(not_(Seat.seat_id.in_(locked_subq)))
                    .scalar()
                )
                options.append(
                    {
                        "index": idx,
                        "show_id": show.show_id,
                        "show_time": show.show_time.strftime("%H:%M") if getattr(show, "show_time", None) else None,
                        "screen_id": screen.screen_id,
                        "screen_name": screen.screen_name,
                        "available_seat_count": int(available_count or 0),
                    }
                )

            if options:
                state["show_options"] = options
                labels = [f"{o['index']}. {o['show_time']} at {o['screen_name']} ({o['available_seat_count']} seats)" for o in options]
                state["awaiting_user"] = True
                state["missing_fields"] = ["show_id"]
                state["next_node"] = "screen"
                state["response"] = "Available shows for that movie on that date:\n" + "\n".join(labels) + "\nReply with the option number or showtime/screen name."
                logger.debug("SCREEN: presenting show options: %s", labels)
                return state
            else:
                # No shows found for that date
                state["awaiting_user"] = True
                state["missing_fields"] = ["show_date"]
                state["next_node"] = "screen"
                state["response"] = "No shows found for that movie on that date. Please pick another date."
                return state

        # Fallback: existing movie listing / resolve behavior (unchanged)
        # If movie_title missing -> present movie options (keeps previous logic)
        movie_options_state = state.get("movie_options")
        if not (movie_title or movie_id):
            # present top active movies (same logic as before)
            movies = (
                db.query(Movie)
                .filter(Movie.is_active == True)
                .order_by(Movie.title.asc())
                .limit(20)
                .all()
            )
            if movies:
                opts = _build_movie_options_from_rows(movies)
                state["movie_options"] = opts
                labels = [f"{o['index']}. {o['title']}" for o in opts]
                state["awaiting_user"] = True
                state["missing_fields"] = ["movie_title"]
                state["next_node"] = "screen"
                state["response"] = "Which movie would you like to watch? Reply with the option number or movie title.\n" + "\n".join(labels)
                return state

        # If movie_title provided and movie_id resolved, and we get here, continue to other nodes
        return state

    finally:
        db.close()