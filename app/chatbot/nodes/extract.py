from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq

from chatbot.state import ChatState, Intent

logger = logging.getLogger("chat_graph.extract")
logger.setLevel(logging.DEBUG)

SYSTEM_PROMPT = """You extract intent and entities for a movie-ticket booking assistant.
Return a JSON object with keys: intent (booking|recommendation|screen_info|cancel|fallback),
movie_title (string or null), show_date (ISO date or null), show_time (HH:MM or null),
screen_name (string or null), booking_id (int or null), seats_requested (int or null), seat_ids (list[int]), language (string or null), format (string or null).
Only extract fields explicitly present in the user's message or that can be reasonably inferred from the provided state context.
If the user is resuming an in-progress booking flow (state.next_node in ['screen','seat','validate','cancel']), prefer keeping intent='booking' or intent='cancel' unless the user clearly requests otherwise.
Do NOT hallucinate facts; set them null if not stated.
"""

# Small few-shot examples to improve accuracy on short resumes
_EXAMPLES = [
    {
        "user": "1",
        "state": {"next_node": "seat", "missing_fields": ["seats_requested"]},
        "json": {"intent": "booking", "seats_requested": 1, "movie_title": None, "show_date": None, "show_time": None, "seat_ids": [], "screen_name": None, "language": None, "format": None},
    },
    {
        "user": "1",
        "state": {"next_node": "screen", "missing_fields": ["movie_title"], "movie_options": [{"index": 1, "title": "Dhurandhar"}, {"index": 2, "title": "Sirai"}]},
        "json": {"intent": "booking", "movie_title": "Sirai", "show_date": None, "show_time": None, "seats_requested": None, "seat_ids": [], "screen_name": None, "language": None, "format": None},
    },
    {
        "user": "09:00 at screen3",
        "state": {"next_node": "screen", "missing_fields": ["show_id"], "show_options": [{"index": 1, "show_time": "09:00", "screen_name": "screen3"}]},
        "json": {"intent": "booking", "show_time": "09:00", "screen_name": "screen3", "show_id": None, "movie_title": None, "seats_requested": None, "seat_ids": []},
    },
    {
        "user": "cancel booking 82",
        "state": {"next_node": "cancel", "missing_fields": ["booking_id"]},
        "json": {"intent": "cancel", "booking_id": 82}
    },
]

_llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.0)


def _parse_relative_date(text: str, ref_date: Optional[date] = None) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if ref_date is None:
        ref_date = date.today()
    if re.search(r"\bday after tomorrow\b", t):
        return (ref_date + timedelta(days=2)).isoformat()
    if re.search(r"\btomorrow\b", t):
        return (ref_date + timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", t):
        return ref_date.isoformat()

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    for name, idx in weekdays.items():
        if re.search(rf"\b(next\s+)?{name}\b", t):
            today_idx = ref_date.weekday()
            days_ahead = (idx - today_idx) % 7
            target = ref_date + timedelta(days=days_ahead) if days_ahead != 0 else ref_date
            return target.isoformat()

    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)

    try_formats = ["%d %b %Y", "%d %B %Y", "%d %b", "%d %B", "%b %d", "%B %d"]
    for fmt in try_formats:
        tokens = re.findall(r"\b[\w]+\b(?:\s+[\w]+\b){0,2}", text)
        for tok in tokens:
            try:
                dt = datetime.strptime(tok, fmt)
                year = dt.year if "%Y" in fmt else ref_date.year
                parsed = date(year, dt.month, dt.day)
                return parsed.isoformat()
            except Exception:
                continue

    return None


def _normalize_time_hm(ts: Optional[str]) -> Optional[str]:
    """Return HH:MM from input like '09:00' or '09:00:00' or '9:0'"""
    if not ts:
        return None
    parts = str(ts).split(":")
    if len(parts) >= 2:
        try:
            h = int(parts[0])
            m = int(parts[1])
            return f"{h:02d}:{m:02d}"
        except Exception:
            return None
    return None


async def extract_entities(state: ChatState) -> ChatState:
    """
    Robust extractor that:
    - Calls LLM with compact state context + few-shot examples.
    - Normalizes show_date/show_time.
    - Preserves booking/cancel intent when resuming appropriate flows.
    - Applies deterministic fallbacks for short replies (dates/numbers/booking ids).
    - Resolves show_options -> show_id when a unique match exists (using parsed OR existing state values).
    - Merges parsed fields safely into existing state (do not overwrite with None).
    """
    user_msg = (state.get("message") or "").strip()

    # Compact context for prompt (limit sizes)
    compact_state = {
        "intent": state.get("intent"),
        "next_node": state.get("next_node"),
        "missing_fields": state.get("missing_fields", []),
        "movie_options": state.get("movie_options", [])[:8],
        "show_options": state.get("show_options", [])[:12],
        "show_date": state.get("show_date"),
    }

    examples_text = "\n\n".join(
        f"User: {ex['user']}\nState: {ex['state']}\nReturn:\n{ex['json']}" for ex in _EXAMPLES
    )

    user_prompt = f"Context: {compact_state}\nUser message: \"{user_msg}\"\n\nExamples:\n{examples_text}\n\nReturn a strict JSON object."

    # Call LLM
    resp = await _llm.ainvoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    parser = JsonOutputParser()
    content = resp.content
    try:
        parsed = parser.parse(content) or {}
    except Exception:
        parsed = {}

    # Normalize parsed intent
    parsed_intent = parsed.get("intent")
    parsed_intent = parsed_intent if parsed_intent in {"booking", "recommendation", "screen_info", "cancel", "fallback"} else "fallback"

    # Preserve booking/cancel intent when resuming booking/cancel flows
    prior_intent = state.get("intent")
    # include 'cancel' so mid-cancel numeric replies remain in cancel flow
    booking_resume_nodes = {"screen", "seat", "validate", "cancel"}
    if prior_intent in ("booking", "cancel") and state.get("next_node") in booking_resume_nodes:
        if parsed_intent not in ("booking", "cancel"):
            logger.debug("EXTRACT: preserving prior intent (parsed=%s, prior=%s)", parsed_intent, prior_intent)
            parsed_intent = prior_intent

    # Normalize show_date: prefer parsed, else try deterministic relative date parse
    show_date_iso: Optional[str] = None
    if parsed.get("show_date"):
        try:
            dt = datetime.fromisoformat(parsed["show_date"])
            show_date_iso = dt.date().isoformat()
        except Exception:
            try:
                # accept YYYY-MM-DD
                _ = datetime.strptime(parsed["show_date"], "%Y-%m-%d")
                show_date_iso = parsed["show_date"]
            except Exception:
                show_date_iso = None
    if not show_date_iso:
        rel = _parse_relative_date(user_msg)
        if rel:
            show_date_iso = rel

    # Normalize show_time to HH:MM:SS if possible
    show_time_iso: Optional[str] = None
    if parsed.get("show_time"):
        st = parsed["show_time"]
        try:
            # Accept "HH:MM" or "HH:MM:SS"
            t = datetime.fromisoformat(f"2020-01-01T{st}").time()
            show_time_iso = t.isoformat()
        except Exception:
            show_time_iso = None

    # Seats and seat_ids
    seat_ids_parsed = parsed.get("seat_ids") or []
    if not isinstance(seat_ids_parsed, list):
        seat_ids_parsed = []
    seats_requested_parsed = parsed.get("seats_requested")
    if isinstance(seats_requested_parsed, float):
        seats_requested_parsed = int(seats_requested_parsed)

    # Deterministic numeric fallback for seats when context expects it
    expecting_seats = False
    try:
        expecting_seats = (
            "seats_requested" in (state.get("missing_fields") or [])
            or state.get("next_node") in ("seat", "validate")
        )
    except Exception:
        expecting_seats = False

    if (not isinstance(seats_requested_parsed, int) or seats_requested_parsed <= 0) and user_msg and expecting_seats:
        m = re.fullmatch(r"\s*(\d+)\s*(?:tickets?|seats?)?\s*$", user_msg.lower())
        if m:
            seats_requested_parsed = int(m.group(1))
            logger.debug("EXTRACT: deterministic fallback parsed seats_requested=%s from message=%r", seats_requested_parsed, user_msg)

    # Deterministic numeric fallback for booking selection when resuming cancel flow
    try:
        expecting_booking_id = (
            "booking_id" in (state.get("missing_fields") or [])
            or state.get("next_node") == "cancel"
        )
    except Exception:
        expecting_booking_id = False

    if expecting_booking_id and user_msg:
        m_booking = re.fullmatch(r"\s*(\d+)\s*$", user_msg)
        if m_booking:
            parsed["booking_id"] = int(m_booking.group(1))
            parsed_intent = "cancel"
            logger.debug("EXTRACT: deterministic fallback parsed booking_id=%s from message=%r", parsed["booking_id"], user_msg)

    # Start merging into a safe new_state (preserve prior values unless we have good parsed/fallback values)
    new_state: ChatState = dict(state)

    # Intent
    new_state["intent"] = parsed_intent if parsed_intent else (prior_intent or "fallback")

    # movie_title
    if parsed.get("movie_title"):
        new_state["movie_title"] = parsed.get("movie_title")

    # show_date
    if show_date_iso is not None:
        new_state["show_date"] = show_date_iso

    # show_time
    if show_time_iso is not None:
        new_state["show_time"] = show_time_iso

    # screen_name
    if parsed.get("screen_name"):
        new_state["screen_name"] = parsed.get("screen_name")

    # booking_id
    if parsed.get("booking_id"):
        try:
            new_state["booking_id"] = int(parsed.get("booking_id"))
        except Exception:
            new_state["booking_id"] = parsed.get("booking_id")

    # seats_requested
    if isinstance(seats_requested_parsed, int) and seats_requested_parsed > 0:
        new_state["seats_requested"] = seats_requested_parsed

    # seat_ids
    if seat_ids_parsed:
        new_state["seat_ids"] = seat_ids_parsed

    # language, format
    if parsed.get("language"):
        new_state["language"] = parsed.get("language")
    if parsed.get("format"):
        new_state["format"] = parsed.get("format")

    # Keep structured options if LLM returned them (rare) — otherwise keep existing server-provided options
    if parsed.get("movie_options"):
        new_state["movie_options"] = parsed.get("movie_options")
    if parsed.get("show_options"):
        new_state["show_options"] = parsed.get("show_options")

    # Deterministically resolve show_options -> concrete show_id when possible.
    # Use parsed values OR existing state values (parsed preferred, fall back to state) so earlier selections are consumed.
    try:
        # Use parsed sources first, then fall back to existing state values
        incoming_show_time = show_time_iso or (state.get("show_time") or new_state.get("show_time"))
        incoming_screen_name = parsed.get("screen_name") or state.get("screen_name") or new_state.get("screen_name")
        opts = state.get("show_options") or new_state.get("show_options") or []
        logger.debug("EXTRACT: resolving show_options: opts_count=%d incoming_show_time=%r incoming_screen_name=%r existing_show_id=%r", len(opts), incoming_show_time, incoming_screen_name, new_state.get("show_id"))
        # Only attempt if we don't already have a show_id
        if opts and not new_state.get("show_id") and (incoming_show_time or incoming_screen_name):
            def _norm(s: Optional[str]) -> str:
                return (s or "").strip().lower()

            matches_exact: List[Dict[str, Any]] = []
            matches_time_only: List[Dict[str, Any]] = []
            matches_screen_only: List[Dict[str, Any]] = []

            in_time_hm = _normalize_time_hm(incoming_show_time)

            for o in opts:
                opt_time = _normalize_time_hm(o.get("show_time"))
                opt_screen = (o.get("screen_name") or "").strip().lower()

                # exact time+screen match
                if in_time_hm and incoming_screen_name and opt_time == in_time_hm and (incoming_screen_name.strip().lower() in opt_screen):
                    matches_exact.append(o)
                    continue
                # time-only match
                if in_time_hm and opt_time == in_time_hm:
                    matches_time_only.append(o)
                    continue
                # screen-only match (loose)
                if incoming_screen_name and (incoming_screen_name.strip().lower() in opt_screen):
                    matches_screen_only.append(o)
                    continue

            # preference: exact matches -> time-only (unique) -> screen-only (unique)
            matches = []
            if len(matches_exact) == 1:
                matches = matches_exact
            elif len(matches_time_only) == 1 and not matches_exact:
                matches = matches_time_only
            elif len(matches_screen_only) == 1 and not matches_exact and not matches_time_only:
                matches = matches_screen_only

            logger.debug("EXTRACT: show_options matching results exact=%d time_only=%d screen_only=%d chosen_count=%d", len(matches_exact), len(matches_time_only), len(matches_screen_only), len(matches))
            if len(matches) == 1:
                chosen = matches[0]
                new_state["show_id"] = chosen.get("show_id")
                # normalize to HH:MM:SS if downstream expects that
                st = chosen.get("show_time")
                if isinstance(st, str) and len(st.split(":")) == 2:
                    st = st + ":00"
                new_state["show_time"] = st
                new_state["screen_id"] = chosen.get("screen_id")
                # consume show_options so screen node doesn't re-present
                new_state.pop("show_options", None)
                # update missing_fields to remove show selection
                new_state["missing_fields"] = [mf for mf in new_state.get("missing_fields", []) if mf not in ("show_id", "show_time")]
                logger.debug("EXTRACT: resolved show selection from show_options -> %s", chosen)
            else:
                logger.debug("EXTRACT: did not find a unique show_options match; leaving for screen node to resolve")
    except Exception:
        logger.exception("EXTRACT: error while resolving show_options match")

    # After merging, clear awaiting_user so nodes can run; nodes will set awaiting_user again if they need input
    new_state["awaiting_user"] = False
    # Preserve previous missing_fields if no change otherwise nodes will recompute it
    new_state["missing_fields"] = new_state.get("missing_fields", state.get("missing_fields", []))

    logger.debug(
        "EXTRACT: merged state intent=%s show_date=%s show_time=%s seats_requested=%s booking_id=%s show_id=%s",
        new_state.get("intent"),
        new_state.get("show_date"),
        new_state.get("show_time"),
        new_state.get("seats_requested"),
        new_state.get("booking_id"),
        new_state.get("show_id"),
    )

    return new_state