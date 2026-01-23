"""
Production-Ready Rescheduling
- Swap underperforming prime slots with high-demand off-prime
- Considers revenue impact
- Maintains constraints
- Safe time swapping
"""
from datetime import date, timedelta, time, datetime
from collections import defaultdict
from database import SessionLocal
from model import Show, Seat, ShowCategoryPricing
from model.theatre import ShowStatusEnum
from model.seat import SeatLock, SeatLockStatusEnum
from agent.state import OpsState
from sqlalchemy import text

PRIME_START = time(18, 0)
PRIME_END = time(23, 0)
TEMP_TIME = time(3, 59, 59)

# Thresholds
CONFIDENCE_THRESHOLD = 0.55
MIN_BOOKING_RATIO = 0.15
UNDERPERFORM_GAP = -0.30  # 30% below forecast
OVERPERFORM_GAP = 0.25    # 25% above forecast


def get_show_revenue(show_id: int, db) -> float:
    """Calculate current revenue for a show"""
    revenue = db.execute(text("""
        SELECT COALESCE(SUM(scp.price), 0) as revenue
        FROM booked_seats bs
        JOIN seats s ON bs.seat_id = s.seat_id
        JOIN show_category_pricing scp ON 
            scp.show_id = bs.show_id AND 
            scp.category_id = s.category_id
        WHERE bs.show_id = :show_id
        AND bs.status = 'BOOKED'
    """), {"show_id": show_id}).scalar()
    
    return float(revenue or 0)


def get_show_potential_revenue(show_id: int, db) -> float:
    """Calculate potential revenue if show fills to capacity"""
    potential = db.execute(text("""
        SELECT COALESCE(SUM(scp.price), 0) as potential
        FROM seats s
        JOIN show_category_pricing scp ON 
            scp.show_id = :show_id AND 
            scp.category_id = s.category_id
        JOIN shows sh ON sh.show_id = :show_id
        WHERE s.screen_id = sh.screen_id
    """), {"show_id": show_id}).scalar()
    
    return float(potential or 0)


def reschedule_node(state: OpsState):
    """
    Intelligent rescheduling with revenue optimization
    """
    db = SessionLocal()
    tomorrow = date.today() + timedelta(days=1)
    
    # Build forecast map (show-level)
    forecast_map = {}
    for s in state.get("result", {}).get("scheduling", []):
        if s.get("show_id") and s.get("date") == str(tomorrow):
            forecast_map[s["show_id"]] = s
    
    # Get constraints
    constraint_map = {
        c["movie"]: c
        for c in state.get("display_constraints", []) or []
    }
    
    # Get tomorrow's shows
    shows = db.query(Show).filter(
        Show.show_date == tomorrow,
        Show.status == ShowStatusEnum.UPCOMING
    ).order_by(Show.screen_id, Show.show_time).all()
    
    if not shows:
        db.close()
        state.setdefault("result", {})
        state["result"]["reschedule"] = []
        state["output"] = "No shows to reschedule."
        return state
    
    # Track shows per movie
    daily_count = defaultdict(int)
    for s in shows:
        daily_count[s.movie_id] += 1
    
    touched = set()
    result = []
    total_revenue_impact = 0
    
    for show in shows:
        if show.show_id in touched:
            continue
        
        if show.show_id not in forecast_map:
            continue
        
        forecast = forecast_map[show.show_id]
        confidence = forecast.get("confidence", 0.5)
        
        # Skip low confidence
        if confidence < CONFIDENCE_THRESHOLD:
            continue
        
        # Get capacity and bookings
        total_seats = db.query(Seat).filter(
            Seat.screen_id == show.screen_id
        ).count() or 1
        
        booked = db.query(SeatLock).filter(
            SeatLock.show_id == show.show_id,
            SeatLock.status == SeatLockStatusEnum.BOOKED
        ).count()
        
        current_occ = booked / total_seats
        
        # Calculate forecast occupancy
        forecast_demand = forecast.get("forecast_demand", 0)
        forecast_occ = forecast_demand / total_seats
        
        gap = forecast_occ - current_occ
        is_prime = PRIME_START <= show.show_time <= PRIME_END
        
        # Get movie constraints
        movie = db.query(Show).join(Show.movie).filter(
            Show.show_id == show.show_id
        ).first()
        
        if not movie:
            continue
        
        movie_name = movie.movie.title
        min_shows = constraint_map.get(movie_name, {}).get("min_shows_per_day", 0)
        
        # Get current revenue
        current_revenue = get_show_revenue(show.show_id, db)
        potential_revenue = get_show_potential_revenue(show.show_id, db)
        
        # =============== RULE 1: CANCEL POOR PERFORMERS ===============
        if (gap < UNDERPERFORM_GAP and 
            current_occ < MIN_BOOKING_RATIO and
            daily_count[show.movie_id] > min_shows and
            current_revenue < potential_revenue * 0.1):  # Less than 10% revenue potential
            
            show.status = ShowStatusEnum.CANCELLED
            daily_count[show.movie_id] -= 1
            touched.add(show.show_id)
            
            result.append({
                "show_id": show.show_id,
                "movie": movie_name,
                "action": "cancelled",
                "gap": round(gap, 2),
                "current_occ": round(current_occ, 2),
                "forecast_occ": round(forecast_occ, 2),
                "current_revenue": round(current_revenue, 2),
                "revenue_impact": -current_revenue,
                "reason": "severe_underperformance"
            })
            
            total_revenue_impact -= current_revenue
            continue
        
        # =============== RULE 2: PROMOTE TO PRIME TIME ===============
        if gap > OVERPERFORM_GAP and not is_prime:
            # Find a lower-performing prime slot
            prime_candidates = [
                s for s in shows
                if (PRIME_START <= s.show_time <= PRIME_END and
                    s.screen_id == show.screen_id and
                    s.show_id != show.show_id and
                    s.show_id not in touched and
                    s.show_id in forecast_map)
            ]
            
            # Sort by underperformance
            prime_candidates_scored = []
            for prime_show in prime_candidates:
                prime_forecast = forecast_map[prime_show.show_id]
                prime_demand = prime_forecast.get("forecast_demand", 0)
                
                prime_total_seats = db.query(Seat).filter(
                    Seat.screen_id == prime_show.screen_id
                ).count() or 1
                
                prime_booked = db.query(SeatLock).filter(
                    SeatLock.show_id == prime_show.show_id,
                    SeatLock.status == SeatLockStatusEnum.BOOKED
                ).count()
                
                prime_occ = prime_booked / prime_total_seats
                prime_forecast_occ = prime_demand / prime_total_seats
                prime_gap = prime_forecast_occ - prime_occ
                
                # Calculate revenue gain from swap
                current_prime_revenue = get_show_revenue(prime_show.show_id, db)
                current_offprime_revenue = get_show_revenue(show.show_id, db)
                
                # Estimate new revenues after swap
                offprime_potential = get_show_potential_revenue(show.show_id, db)
                prime_potential = get_show_potential_revenue(prime_show.show_id, db)
                
                # High-demand movie in prime = more revenue
                estimated_new_prime_revenue = offprime_potential * forecast_occ * confidence
                estimated_new_offprime_revenue = prime_potential * prime_occ * 0.8  # Discount for off-prime
                
                revenue_gain = (estimated_new_prime_revenue + estimated_new_offprime_revenue) - \
                              (current_prime_revenue + current_offprime_revenue)
                
                prime_candidates_scored.append((prime_gap, revenue_gain, prime_show))
            
            if prime_candidates_scored:
                # Pick best candidate (most underperforming or best revenue gain)
                prime_candidates_scored.sort(key=lambda x: (x[0], -x[1]))
                prime_gap, revenue_gain, prime_show = prime_candidates_scored[0]
                
                # Only swap if revenue positive or prime is severely underperforming
                if revenue_gain > 0 or prime_gap < -0.2:
                    # Safe swap using temp time
                    t1, t2 = show.show_time, prime_show.show_time
                    show.show_time = TEMP_TIME
                    db.flush()
                    prime_show.show_time = t1
                    db.flush()
                    show.show_time = t2
                    
                    touched.add(show.show_id)
                    touched.add(prime_show.show_id)
                    
                    result.append({
                        "show_id": show.show_id,
                        "movie": movie_name,
                        "action": "promoted_to_prime",
                        "swapped_with": prime_show.show_id,
                        "old_time": str(t1),
                        "new_time": str(t2),
                        "gap": round(gap, 2),
                        "prime_gap": round(prime_gap, 2),
                        "revenue_impact": round(revenue_gain, 2),
                        "reason": "demand_optimization"
                    })
                    
                    total_revenue_impact += revenue_gain
                    continue
        
       
        if gap < UNDERPERFORM_GAP and is_prime:
            # Find high-demand off-prime slot
            offprime_candidates = [
                s for s in shows
                if (s.show_time < PRIME_START and
                    s.screen_id == show.screen_id and
                    s.show_id != show.show_id and
                    s.show_id not in touched and
                    s.show_id in forecast_map)
            ]
            
            offprime_candidates_scored = []
            for offprime_show in offprime_candidates:
                offprime_forecast = forecast_map[offprime_show.show_id]
                offprime_demand = offprime_forecast.get("forecast_demand", 0)
                
                offprime_total_seats = db.query(Seat).filter(
                    Seat.screen_id == offprime_show.screen_id
                ).count() or 1
                
                offprime_booked = db.query(SeatLock).filter(
                    SeatLock.show_id == offprime_show.show_id,
                    SeatLock.status == SeatLockStatusEnum.BOOKED
                ).count()
                
                offprime_occ = offprime_booked / offprime_total_seats
                offprime_forecast_occ = offprime_demand / offprime_total_seats
                offprime_gap = offprime_forecast_occ - offprime_occ
                
                # Prefer high-demand off-prime shows
                if offprime_gap > 0.15:
                    offprime_candidates_scored.append((offprime_gap, offprime_show))
            
            if offprime_candidates_scored:
                offprime_candidates_scored.sort(key=lambda x: -x[0])
                offprime_gap, offprime_show = offprime_candidates_scored[0]
                
                # Safe swap
                t1, t2 = show.show_time, offprime_show.show_time
                show.show_time = TEMP_TIME
                db.flush()
                offprime_show.show_time = t1
                db.flush()
                show.show_time = t2
                
                touched.add(show.show_id)
                touched.add(offprime_show.show_id)
                
                result.append({
                    "show_id": show.show_id,
                    "movie": movie_name,
                    "action": "demoted_from_prime",
                    "swapped_with": offprime_show.show_id,
                    "old_time": str(t1),
                    "new_time": str(t2),
                    "gap": round(gap, 2),
                    "offprime_gap": round(offprime_gap, 2),
                    "revenue_impact": 0,  # Neutral or slight negative
                    "reason": "prime_slot_optimization"
                })
    
    db.commit()
    db.close()
    
    state.setdefault("result", {})
    state["result"]["reschedule"] = result
    state["result"]["reschedule_revenue_impact"] = round(total_revenue_impact, 2)
    
    actions = defaultdict(int)
    for r in result:
        actions[r["action"]] += 1
    
    state["output"] = (
        f"Rescheduling: {actions['cancelled']} cancelled, "
        f"{actions['promoted_to_prime']} promoted, "
        f"{actions['demoted_from_prime']} demoted. "
        f"Revenue impact: ₹{round(total_revenue_impact, 2)}"
    )
    
    return state