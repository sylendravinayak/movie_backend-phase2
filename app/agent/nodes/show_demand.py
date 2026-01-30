from langgraph.errors import NodeInterrupt
from agent.state import OpsState
from database import SessionLocal
from model import Show
from model.seat import Seat
from model.theatre import ShowStatusEnum
from collections import defaultdict
from datetime import datetime

def normalize_to_fixed_slot(time_str: str) -> str:
    """
    Map any HH:MM time to nearest FIXED_TIME_SLOTS bucket
    """
    h, m = map(int, time_str.split(":"))
    minutes = h * 60 + m

    slot_minutes = {
        "09:00": 9 * 60,
        "12:00": 12 * 60,
        "15:00": 15 * 60,
        "18:00": 18 * 60,
        "21:00": 21 * 60,
    }

    return min(slot_minutes, key=lambda k: abs(slot_minutes[k] - minutes))

def expand_slot_forecast_to_show_level(state: OpsState):
    """
    Convert SLOT-LEVEL forecast into SHOW-LEVEL forecast
    using FIXED_TIME_SLOTS bucketing
    """

    slot_forecast = state.get("result", {}).get("forecast")
    if not slot_forecast:
        raise NodeInterrupt("slot_forecast missing or empty")

    db = SessionLocal()

    shows = db.query(Show).filter(
        Show.status == ShowStatusEnum.UPCOMING
    ).all()

    if not shows:
        db.close()
        raise NodeInterrupt("No upcoming shows found for slot expansion")

    # -------------------- INDEX SHOWS (NORMALIZED SLOTS) --------------------
    shows_by_key = defaultdict(list)

    for show in shows:
        normalized_slot = normalize_to_fixed_slot(
            show.show_time.strftime("%H:%M")
        )

        key = (
            show.movie_id,
            show.show_date.strftime("%Y-%m-%d"),
            normalized_slot
        )
        shows_by_key[key].append(show)

    # -------------------- SCREEN CAPACITY CACHE --------------------
    screen_capacity = {}
    for show in shows:
        if show.screen_id not in screen_capacity:
            screen_capacity[show.screen_id] = db.query(Seat).filter(
                Seat.screen_id == show.screen_id
            ).count()

    # -------------------- EXPANSION --------------------
    show_forecast = {}
    dropped_slots = 0

    for slot_row in slot_forecast:
        normalized_slot = normalize_to_fixed_slot(slot_row["slot"])

        key = (
            slot_row["movie_id"],
            slot_row["date"],
            normalized_slot
        )

        matching_shows = shows_by_key.get(key)

        if not matching_shows:
            dropped_slots += 1
            continue

        total_capacity = sum(
            screen_capacity.get(show.screen_id, 0)
            for show in matching_shows
        ) or 1

        slot_demand = slot_row["slot_expected_demand"]
        base_confidence = slot_row.get("confidence", 0.5)

        for show in matching_shows:
            cap = screen_capacity.get(show.screen_id, 0) or 1
            demand_share = cap / total_capacity
            show_demand = slot_demand * demand_share
            fill_ratio = show_demand / cap

            show_forecast[show.show_id] = {
                "show_id": show.show_id,
                "movie_id": show.movie_id,
                "movie": slot_row["movie"],
                "date": slot_row["date"],
                "slot": normalized_slot,  # 👈 fixed bucket
                "forecast_demand": round(show_demand, 2),

                # ✅ capacity-aware fields
                "screen_capacity": cap,
                "fill_ratio": round(fill_ratio, 2),

                "confidence": base_confidence,
                "is_prime": slot_row.get("is_prime_slot", False),
                "source": "slot_expansion",
                "movie_day_demand": slot_row["movie_day_demand"]
            }

    db.close()

    if not show_forecast:
        raise NodeInterrupt(
            "Slot→Show expansion produced empty forecast (no matching shows)"
        )

    state["result"]["show_forecast"] = list(show_forecast.values())
    state["forecast_scope"] = "show_level"

    state["debug"] = {
        "slot_rows_processed": len(slot_forecast),
        "shows_generated": len(show_forecast),
        "slots_dropped_no_show_match": dropped_slots
    }

    return state