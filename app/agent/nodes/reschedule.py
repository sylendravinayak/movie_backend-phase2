from datetime import date, timedelta, time
from collections import defaultdict
from database import SessionLocal
from model import Show, Seat
from model.theatre import ShowStatusEnum
from agent.state import OpsState
from agent.tools.constraint_manager import ConstraintManager

# --- SLOT DEFINITIONS (MATCH SCHEDULER) ---
FIXED_TIME_SLOTS = ["09:00", "12:00", "15:00", "18:00", "21:00"]
PRIME_SLOTS = {"18:00", "21:00"}

MAX_CAPACITY_RATIO = 1.05   # HARD LIMIT
SPLIT_THRESHOLD = 1.40      # split if insane demand


def reschedule_node(state: OpsState):
    """
    BRUTALLY FIXED rescheduling node
    - Forecast-driven
    - Capacity-first
    - No booking dependency
    - Deterministic
    """

    db = SessionLocal()
    tomorrow = date.today() + timedelta(days=1)

    show_forecasts = state.get("result", {}).get("show_forecast", [])
    if not show_forecasts:
        state.setdefault("result", {})
        state["result"]["reschedule"] = []
        state["output"] = "No show-level forecasts available."
        return state

    # Map forecasts by show_id
    forecast_map = {f["show_id"]: f for f in show_forecasts}

    shows = db.query(Show).filter(
        Show.show_date == tomorrow,
        Show.status == ShowStatusEnum.UPCOMING
    ).all()

    if not shows:
        state.setdefault("result", {})
        state["result"]["reschedule"] = []
        state["output"] = "No upcoming shows found."
        return state

    # Index shows by (date, slot)
    shows_by_slot = defaultdict(list)
    for s in shows:
        slot = s.show_time.strftime("%H:%M")
        shows_by_slot[(s.show_date, slot)].append(s)

    manager = ConstraintManager(db)
    merged_constraints = state.get("merged_constraints", {})

    result = []
    touched = set()
    total_revenue_impact = 0
    constraint_violations = 0

    for show in shows:
        if show.show_id in touched:
            continue

        forecast = forecast_map.get(show.show_id)
        if not forecast:
            continue

        slot = forecast["slot"]
        fill_ratio = forecast.get("fill_ratio", 0)
        is_prime = slot in PRIME_SLOTS
        movie_id = str(show.movie_id)
        movie_name = forecast["movie"]

        # --- HARD RULE: IGNORE HEALTHY SHOWS ---
        if fill_ratio <= MAX_CAPACITY_RATIO:
            continue

        # --- CONSTRAINT CHECK ---
        merged = merged_constraints.get(movie_id, {})
        if merged.get("prime_time_required", False) and not is_prime:
            constraint_violations += 1
            result.append({
                "show_id": show.show_id,
                "movie": movie_name,
                "action": "skip_reschedule",
                "reason": "prime_time_required_constraint"
            })
            continue

        # --- CASE 1: NON-PRIME OVERFLOW → PROMOTE ---
        if not is_prime:
            prime_candidates = []

            for prime_slot in PRIME_SLOTS:
                for prime_show in shows_by_slot.get((show.show_date, prime_slot), []):
                    if prime_show.show_id in touched:
                        continue
                    if prime_show.show_id not in forecast_map:
                        continue
                    prime_candidates.append(prime_show)

            if prime_candidates:
                target = prime_candidates[0]  # deterministic
                old_slot = slot
                new_slot = target.show_time.strftime("%H:%M")

                # swap times safely
                show.show_time, target.show_time = target.show_time, show.show_time
                db.flush()

                touched.add(show.show_id)
                touched.add(target.show_id)

                result.append({
                    "show_id": show.show_id,
                    "movie": movie_name,
                    "action": "promoted_to_prime",
                    "old_slot": old_slot,
                    "new_slot": new_slot,
                    "fill_ratio": round(fill_ratio, 2),
                    "reason": "over_capacity"
                })
                continue

        # --- CASE 2: PRIME OVERFLOW → SCREEN UPGRADE OR SPLIT ---
        if is_prime:
            capacity = forecast.get("screen_capacity", 0)

            if fill_ratio >= SPLIT_THRESHOLD:
                result.append({
                    "show_id": show.show_id,
                    "movie": movie_name,
                    "action": "split_recommended",
                    "slot": slot,
                    "fill_ratio": round(fill_ratio, 2),
                    "reason": "extreme_overflow"
                })
                continue

            result.append({
                "show_id": show.show_id,
                "movie": movie_name,
                "action": "screen_upgrade_recommended",
                "slot": slot,
                "fill_ratio": round(fill_ratio, 2),
                "reason": "prime_overflow"
            })

    db.commit()
    db.close()

    state.setdefault("result", {})
    state["result"]["reschedule"] = result
    state["result"]["reschedule_revenue_impact"] = total_revenue_impact
    state["result"]["constraint_violations_prevented"] = constraint_violations

    state["output"] = (
        f"Reschedule actions: {len(result)} | "
        f"Constraints prevented: {constraint_violations}"
    )

    return state