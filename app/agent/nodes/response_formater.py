from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

# =========================================================
# ===================== META ==============================
# =========================================================

class Meta(BaseModel):
    forecast_days: int
    generated_at: str


# =========================================================
# ================= FRONTEND MODELS =======================
# =========================================================

class ForecastSlot(BaseModel):
    movie: str
    date: str
    slot: str
    expected_demand: float
    is_prime: bool


class ShowIssue(BaseModel):
    show_id: int
    movie: str
    slot: str
    capacity: int
    expected_demand: float
    fill_ratio: float


class Action(BaseModel):
    show_id: int
    type: str
    reason: str


class CategoryPriceChange(BaseModel):
    category_id: int
    old_price: float
    new_price: float


class PriceUpdate(BaseModel):
    show_id: int
    movie: str
    slot: str
    action: str
    categories: List[CategoryPriceChange]


class ScheduledShow(BaseModel):
    show_id: int
    movie: str
    screen: str
    date: str
    time: str
    is_prime: bool
    expected_fill: float


# =========================================================
# ===================== FORMATTERS ========================
# =========================================================

def format_optimize(state: Dict[str, Any]) -> Dict[str, Any]:
    forecast = []
    shows = []
    actions = []

    for f in state.get("forecast", []):
        forecast.append(
            ForecastSlot(
                movie=f.get("movie"),
                date=f.get("date"),
                slot=f.get("slot"),
                expected_demand=round(f.get("slot_expected_demand", 0), 2),
                is_prime=f.get("is_prime", False)
            ).dict()
        )

    for r in state.get("reschedule_decisions", []):
        expected = r.get("expected_demand", 0)
        capacity = r.get("capacity", 1)  # prevent div-by-zero

        shows.append(
            ShowIssue(
                show_id=r.get("show_id"),
                movie=r.get("movie"),
                slot=r.get("from_slot"),
                capacity=capacity,
                expected_demand=expected,
                fill_ratio=round(expected / capacity, 2)
            ).dict()
        )

        actions.append(
            Action(
                show_id=r.get("show_id"),
                type=r.get("action"),
                reason=r.get("reason")
            ).dict()
        )

    return {
        "forecast": forecast,
        "shows": shows,
        "actions": actions,
        "pricing": []
    }


def format_pricing(state: Dict[str, Any]) -> Dict[str, Any]:
    pricing = []

    for p in state.get("pricing_decisions", []):
        categories = []

        for c in p.get("category_changes", []):
            categories.append(
                CategoryPriceChange(
                    category_id=c.get("category_id"),
                    old_price=c.get("old_price"),
                    new_price=c.get("new_price")
                ).dict()
            )

        pricing.append(
            PriceUpdate(
                show_id=p.get("show_id"),
                movie=p.get("movie"),
                slot=p.get("slot"),
                action=p.get("action"),
                categories=categories
            ).dict()
        )

    return {
        "forecast": [],
        "shows": [],
        "actions": [],
        "pricing": pricing
    }


def format_scheduling(state: Dict[str, Any]) -> Dict[str, Any]:
    shows = []

    for s in state.get("final_schedule", []):
        shows.append(
            ScheduledShow(
                show_id=s.get("show_id"),
                movie=s.get("movie"),
                screen=s.get("screen"),
                date=s.get("date"),
                time=s.get("time"),
                is_prime=s.get("is_prime", False),
                expected_fill=round(s.get("expected_fill", 0), 2)
            ).dict()
        )

    return {
        "forecast": [],
        "shows": shows,
        "actions": [],
        "pricing": []
    }


# =========================================================
# ===================== RESPONSE NODE =====================
# =========================================================

def response_formatter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    intent = state.get("intent")
    now = datetime.utcnow().isoformat()

    if not intent:
        raise ValueError("State missing required key: intent")

    if intent == "optimize":
        data = format_optimize(state)
        forecast_days = 1

    elif intent == "pricing":
        data = format_pricing(state)
        forecast_days = 1

    elif intent == "scheduling":
        data = format_scheduling(state)
        forecast_days = state.get("horizon_days", 14)

    else:
        raise ValueError(f"Unsupported intent: {intent}")

    return {
        "intent": intent,
        "meta": Meta(
            forecast_days=forecast_days,
            generated_at=now
        ).dict(),
        "data": data
    }