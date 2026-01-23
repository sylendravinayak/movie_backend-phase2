"""
Intelligent Bidirectional Dynamic Pricing
- Increases prices for high demand
- Decreases prices for low demand
- Considers current occupancy + forecast
- Time-to-show urgency pricing
- Competitive pricing
"""
from agent.state import OpsState
from database import SessionLocal
from model import ShowCategoryPricing, SeatCategory, Show
from sqlalchemy import text
from datetime import datetime, timedelta
import math

# Price boundaries
MIN_PRICE_RATIO = 0.65
MAX_PRICE_RATIO = 1.60

# Surge pricing thresholds
HIGH_DEMAND_THRESHOLD = 0.75  # 75% capacity
LOW_DEMAND_THRESHOLD = 0.30   # 30% capacity

def calculate_time_urgency(show_datetime: datetime) -> float:
    """
    Calculate urgency multiplier based on time until show
    Last-minute bookings = higher prices
    """
    now = datetime.now()
    hours_until_show = (show_datetime - now).total_seconds() / 3600
    
    if hours_until_show < 0:
        return 1.0  # Show already started
    elif hours_until_show < 6:
        return 1.15  # Last 6 hours = premium
    elif hours_until_show < 24:
        return 1.08  # Last 24 hours = slight premium
    elif hours_until_show < 48:
        return 1.02
    else:
        return 1.0

def calculate_demand_surge(forecast_occ: float, current_occ: float, 
                          confidence: float) -> float:
    """
    Calculate surge multiplier based on demand
    Returns: multiplier in range [0.7, 1.5]
    """
    
    # Weighted combination (forecast matters more for future, current for near-term)
    effective_occ = (forecast_occ * 0.6) + (current_occ * 0.4)
    effective_occ = min(effective_occ * confidence, 1.0)  # Cap at 100%
    
    if effective_occ >= HIGH_DEMAND_THRESHOLD:
        # HIGH DEMAND → INCREASE PRICES
        # Scale from 1.0 to 1.5 as occupancy goes 75% → 100%
        surge = 1.0 + (effective_occ - HIGH_DEMAND_THRESHOLD) * 2.0
        return min(surge, 1.5)
    
    elif effective_occ <= LOW_DEMAND_THRESHOLD:
        # LOW DEMAND → DECREASE PRICES
        # Scale from 1.0 to 0.7 as occupancy goes 30% → 0%
        discount = 1.0 - (LOW_DEMAND_THRESHOLD - effective_occ) * 1.0
        return max(discount, 0.7)
    
    else:
        # NORMAL DEMAND → Minor adjustments
        # Linear interpolation between 0.95 and 1.05
        range_size = HIGH_DEMAND_THRESHOLD - LOW_DEMAND_THRESHOLD
        position = (effective_occ - LOW_DEMAND_THRESHOLD) / range_size
        return 0.95 + (position * 0.10)

def get_slot_multiplier(hour: int) -> float:
    """Time-of-day pricing multipliers"""
    # Prime time (6pm-11pm) = premium
    if 18 <= hour < 23:
        return 1.12
    # Afternoon (2pm-6pm) = slight premium
    elif 14 <= hour < 18:
        return 1.04
    # Morning/late night = discount
    else:
        return 0.92

def get_day_multiplier(show_date: datetime.date) -> float:
    """Day-of-week pricing multipliers"""
    dow = show_date.weekday()  # 0=Monday, 6=Sunday
    
    # Weekend (Fri, Sat, Sun) = premium
    if dow in [4, 5, 6]:
        return 1.08
    # Weekday = standard/slight discount
    else:
        return 0.98


def pricing_node(state: OpsState):
    """Intelligent bidirectional dynamic pricing"""
    
    db = SessionLocal()
    
    # Collect show IDs
    show_ids = set()
    show_ids.update(state.get("show_ids", []))
    if state.get("show_id"):
        show_ids.add(state["show_id"])
    show_ids.update(state.get("result", {}).get("scheduled_show_ids", []))
    
    for r in state.get("result", {}).get("reschedule", []):
        if r.get("show_id"):
            show_ids.add(r["show_id"])
    
    show_ids = list(show_ids)
    
    if not show_ids:
        db.close()
        state["output"] = "No shows to price"
        return state
    
    # Build forecast map
    forecast_map = {}
    for sched in state.get("result", {}).get("scheduling", []):
        if "show_id" in sched:
            forecast_map[sched["show_id"]] = sched
    
    pricing_results = []
    price_increases = 0
    price_decreases = 0
    
    for show_id in show_ids:
        show = db.query(Show).filter(Show.show_id == show_id).first()
        if not show:
            continue
        
        # Get capacity
        capacity = db.execute(text("""
            SELECT COUNT(*) FROM seats WHERE screen_id = :sid
        """), {"sid": show.screen_id}).scalar() or 1
        
        # Get current bookings
        booked = db.execute(text("""
            SELECT COUNT(*) FROM booked_seats 
            WHERE show_id = :show_id
        """), {"show_id": show_id}).scalar() or 0
        
        current_occ = booked / capacity
        
        # Get forecast
        forecast = forecast_map.get(show_id, {})
        forecast_demand = forecast.get("forecast_demand", capacity * 0.5)
        confidence = forecast.get("confidence", 0.65)
        
        forecast_occ = forecast_demand / capacity
        
        # Calculate pricing multipliers
        show_datetime = datetime.combine(show.show_date, show.show_time)
        
        demand_surge = calculate_demand_surge(forecast_occ, current_occ, confidence)
        time_urgency = calculate_time_urgency(show_datetime)
        slot_mult = get_slot_multiplier(show.show_time.hour)
        day_mult = get_day_multiplier(show.show_date)
        
        # Combined multiplier
        price_multiplier = demand_surge * time_urgency * slot_mult * day_mult
        
        # Apply confidence damping (don't be too aggressive with uncertain forecasts)
        if confidence < 0.6:
            # Pull multiplier towards 1.0
            price_multiplier = 1.0 + (price_multiplier - 1.0) * confidence
        
        # Enforce hard boundaries
        price_multiplier = max(MIN_PRICE_RATIO, min(price_multiplier, MAX_PRICE_RATIO))
        
        # Get or create pricing rows
        pricing_rows = db.query(ShowCategoryPricing).filter(
            ShowCategoryPricing.show_id == show_id
        ).all()
        
        if not pricing_rows:
            categories = db.query(SeatCategory).all()
            for c in categories:
                row = ShowCategoryPricing(
                    show_id=show_id,
                    category_id=c.category_id,
                    price=c.base_price
                )
                db.add(row)
                pricing_rows.append(row)
            db.commit()
        
        # Update prices
        updates = []
        for row in pricing_rows:
            base_price = db.query(SeatCategory.base_price).filter(
                SeatCategory.category_id == row.category_id
            ).scalar() or row.price
            
            old_price = float(row.price)
            new_price = base_price * price_multiplier
            
            # Round to nearest 5
            new_price = round(new_price / 5) * 5
            
            # Enforce boundaries relative to base
            new_price = max(base_price * MIN_PRICE_RATIO, new_price)
            new_price = min(base_price * MAX_PRICE_RATIO, new_price)
            
            # Track direction
            if new_price > old_price:
                price_increases += 1
            elif new_price < old_price:
                price_decreases += 1
            
            row.price = new_price
            
            updates.append({
                "category_id": row.category_id,
                "base_price": base_price,
                "old_price": old_price,
                "new_price": new_price,
                "change_pct": round(((new_price - old_price) / old_price) * 100, 1) if old_price > 0 else 0
            })
        
        pricing_results.append({
            "show_id": show_id,
            "forecast_demand": round(forecast_demand, 2),
            "capacity": capacity,
            "current_occupancy": round(current_occ, 2),
            "forecast_occupancy": round(forecast_occ, 2),
            "demand_surge": round(demand_surge, 2),
            "time_urgency": round(time_urgency, 2),
            "slot_multiplier": round(slot_mult, 2),
            "day_multiplier": round(day_mult, 2),
            "price_multiplier": round(price_multiplier, 2),
            "confidence": round(confidence, 2),
            "hours_until_show": round((show_datetime - datetime.now()).total_seconds() / 3600, 1),
            "pricing_updates": updates,
            "pricing_action": "increase" if price_multiplier > 1.05 else "decrease" if price_multiplier < 0.95 else "hold"
        })
    
    db.commit()
    db.close()
    
    state.setdefault("result", {})
    state["result"]["pricing"] = pricing_results
    state["output"] = (
        f"Dynamic pricing: {price_increases} increases, {price_decreases} decreases, "
        f"{len(pricing_results) - price_increases - price_decreases} holds. "
        f"Total: {len(pricing_results)} shows."
    )
    
    return state