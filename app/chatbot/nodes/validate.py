from __future__ import annotations

import logging
from typing import Any

from chatbot.state import ChatState

logger = logging.getLogger("chat_graph.validate")
logger.setLevel(logging.DEBUG)

# Required fields for booking flow
CRITICAL_FIELDS = ["movie_title", "show_date", "show_time", "seats_requested"]


def _is_missing(value: Any) -> bool:
    """
    Return True for None, empty string, empty container, or invalid seats_requested.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        return True
    return False


async def validate_booking_request(state: ChatState) -> ChatState:
    """
    Validation node with improved UX:
    - If none of the critical fields are present at all, allow screen node to run.
    - If movie_title is missing, delegate selection to the screen node (so it can show movies filtered by date).
    - If movie (title or id) and show_date are present but show_time is missing, delegate to screen to show the day's show options.
    - Otherwise, if user provided partial info (and movie_title present), ask only for the remaining missing fields.
    """
    # Ensure keys exist in state for clarity (do not overwrite existing values)
    for k in CRITICAL_FIELDS:
        if k not in state:
            state[k] = None

    # Log incoming values for debugging
    try:
        logger.debug(
            "ENTER validate_booking_request with keys: %s",
            {k: state.get(k) for k in CRITICAL_FIELDS + ["awaiting_user", "next_node", "movie_id"]},
        )
    except Exception:
        pass

    # If user provided none of the critical fields, do not interrupt here; allow screen node to run.
    any_present = any(not _is_missing(state.get(k)) for k in CRITICAL_FIELDS)

    if not any_present:
        state["missing_fields"] = []
        state["awaiting_user"] = False
        state["next_node"] = None
        state["response"] = None
        logger.debug("VALIDATE: nothing provided; allowing screen node to run and present options")
        return state

    # If movie_title is missing, delegate movie selection to the screen node
    if _is_missing(state.get("movie_title")):
        state["missing_fields"] = ["movie_title"]
        state["awaiting_user"] = False
        state["next_node"] = None
        state["response"] = None
        logger.debug("VALIDATE: movie_title missing; delegating to screen node (will present movie options)")
        return state

    # If we have movie context (either movie_title or movie_id) and we have a show_date,
    # but show_time is missing, delegate to screen to present show options for that day.
    movie_present = (not _is_missing(state.get("movie_title"))) or (state.get("movie_id") is not None)
    if movie_present and not _is_missing(state.get("show_date")) and _is_missing(state.get("show_time")):
        # mark missing_fields for client but do not set awaiting_user here so screen can run
        state["missing_fields"] = ["show_time"]
        state["awaiting_user"] = False
        state["next_node"] = None
        state["response"] = None
        logger.debug("VALIDATE: movie+date present but show_time missing; delegating to screen to list shows")
        return state

    # Otherwise, user provided partial info with movie_title present — compute other missing fields and ask only for them.
    missing = []
    for f in CRITICAL_FIELDS:
        val = state.get(f)
        if f == "seats_requested":
            if not isinstance(val, int) or val <= 0:
                missing.append(f)
        else:
            if _is_missing(val):
                missing.append(f)

    if missing:
        prompts = {
            "movie_title": "Which movie would you like to watch?",
            "show_date": "For which date?",
            "show_time": "What showtime works for you?",
            "seats_requested": "How many tickets do you need?",
        }
        ask = [prompts[m] for m in missing if m in prompts]
        prompt_text = "I need a bit more info: " + " ".join(ask)

        state["missing_fields"] = missing
        state["awaiting_user"] = True
        state["next_node"] = "validate"
        state["response"] = prompt_text

        logger.debug("INTERRUPT validate: missing=%s response=%s", missing, prompt_text)
        return state

    # No missing fields (all present and valid) — continue
    state["missing_fields"] = []
    state["awaiting_user"] = False
    state["next_node"] = None
    state["response"] = None

    logger.debug("VALIDATE OK; continuing flow")
    return state