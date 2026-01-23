"""
Optimal Scheduling with Constraint Satisfaction
- Respects min/max shows per day
- Prime time quota allocation
- Revenue-maximizing screen assignment
- Conflict-free scheduling
"""
from collections import defaultdict
from sqlalchemy import text
from database import SessionLocal
from agent.state import OpsState
from model import Screen, Show, Movie
from datetime import datetime, timedelta, date as dt_date
from typing import List, Dict, Tuple
import heapq

SLOT_DURATION_MIN = 120
PRIME_SLOTS = {"18:20", "20:40"}


class SchedulingOptimizer:
    """Constraint-based optimal scheduling"""
    
    def __init__(self, db, screens, constraints):
        self.db = db
        self.screens = screens
        self.constraints = constraints or {}
        self.screen_capacity = self._get_screen_capacities()
        
    def _get_screen_capacities(self) -> Dict[int, int]:
        """Get seat count for each screen"""
        capacities = {}
        for screen in self.screens:
            cap = self.db.execute(
                text("SELECT COUNT(*) FROM seats WHERE screen_id = :sid"),
                {"sid": screen.screen_id}
            ).scalar() or 1
            capacities[screen.screen_id] = cap
        return capacities
    
    def select_optimal_screen(self, forecast_demand: float, 
                             slot: str, date: str, 
                             used_screens: set) -> Screen:
        """
        Select best screen for this show
        Priority: capacity match > screen quality > availability
        """
        
        available_screens = [
            s for s in self.screens 
            if s.screen_id not in used_screens
        ]
        
        if not available_screens:
            return None
        
        # Score each screen
        scored = []
        for screen in available_screens:
            capacity = self.screen_capacity[screen.screen_id]
            
            # Capacity match score (prefer screens that match demand)
            if capacity == 0:
                match_score = 0
            else:
                utilization = forecast_demand / capacity
                # Ideal utilization is 60-80%
                if 0.6 <= utilization <= 0.8:
                    match_score = 1.0
                elif utilization > 0.8:
                    match_score = 0.8  # Overselling is okay
                else:
                    match_score = max(0.3, utilization / 0.6)  # Underselling is wasteful
            
            # Size score (larger screens for prime time)
            if slot in PRIME_SLOTS:
                size_score = capacity / max(self.screen_capacity.values())
            else:
                size_score = 1.0
            
            total_score = match_score * 0.7 + size_score * 0.3
            
            scored.append((total_score, capacity, screen))
        
        # Sort by score (highest first), then by capacity (largest first)
        scored.sort(key=lambda x: (-x[0], -x[1]))
        
        return scored[0][2]
    
    def check_conflicts(self, screen_id: int, show_date: dt_date, 
                       slot_time: str) -> bool:
        """Check if slot is available"""
        
        time_obj = datetime.strptime(slot_time, "%H:%M").time()
        
        conflict = self.db.query(Show).filter(
            Show.screen_id == screen_id,
            Show.show_date == show_date,
            Show.show_time == time_obj,
            Show.status == "UPCOMING"
        ).first()
        
        return conflict is not None
    
    def allocate_prime_slots(self, forecasts_by_date: Dict, 
                            movie_constraints: Dict) -> Dict:
        """
        Pre-allocate prime slots based on quotas
        Returns: {(date, slot): movie_id} allocation
        """
        
        allocation = {}
        
        for date_str, slot_forecasts in forecasts_by_date.items():
            # Get prime slot forecasts, sorted by demand
            prime_forecasts = [
                f for f in slot_forecasts 
                if f["slot"] in PRIME_SLOTS
            ]
            prime_forecasts.sort(key=lambda x: x["slot_expected_demand"], reverse=True)
            
            # Track prime slots assigned per movie
            prime_assigned = defaultdict(int)
            
            for forecast in prime_forecasts:
                movie_name = forecast["movie"]
                movie_id = forecast["movie_id"]
                slot = forecast["slot"]
                
                # Check quota
                constraints = movie_constraints.get(movie_name, {})
                prime_quota = constraints.get("prime_show_quota", 999)
                
                if prime_assigned[movie_id] < prime_quota:
                    allocation[(date_str, slot, movie_id)] = True
                    prime_assigned[movie_id] += 1
        
        return allocation
    
    def enforce_min_max_shows(self, scheduled_by_date: Dict,
                             movie_constraints: Dict,
                             forecasts_by_date: Dict) -> List[Dict]:
        """
        Ensure min/max shows constraints are met
        Add or remove shows as needed
        """
        
        additional_shows = []
        
        for date_str, movie_counts in scheduled_by_date.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            for movie_name, constraints in movie_constraints.items():
                min_shows = constraints.get("min_shows_per_day", 0)
                max_shows = constraints.get("max_shows_per_day", 999)
                
                # Find movie_id
                movie = self.db.query(Movie).filter(Movie.title == movie_name).first()
                if not movie:
                    continue
                
                current_count = movie_counts.get(movie.movie_id, 0)
                
                # Need more shows to meet minimum
                if current_count < min_shows:
                    slots_needed = min_shows - current_count
                    
                    # Add shows in available slots
                    all_slots = ["09:00", "11:20", "13:40", "16:00", "18:20", "20:40"]
                    
                    for slot in all_slots:
                        if slots_needed <= 0:
                            break
                        
                        additional_shows.append({
                            "movie_id": movie.movie_id,
                            "movie": movie_name,
                            "date": date_str,
                            "slot": slot,
                            "slot_expected_demand": 0,
                            "confidence": 0.5,
                            "reason": "min_constraint"
                        })
                        slots_needed -= 1
        
        return additional_shows


def scheduling_node(state: OpsState):
    """Optimal scheduling with constraints and dynamic slots"""
    
    db = SessionLocal()
    
    forecasts = state.get("result", {}).get("forecast", [])
    if not forecasts:
        db.close()
        state["output"] = "No forecasts available"
        return state
    
    screens = db.query(Screen).filter(Screen.is_available == True).all()
    if not screens:
        db.close()
        state["output"] = "No available screens"
        return state
    
    # Get constraints
    constraint_map = {
        c["movie"]: c
        for c in state.get("display_constraints", []) or []
    }
    
    optimizer = SchedulingOptimizer(db, screens, constraint_map)
    
    # Import slot calculator
    from agent.tools.slot_calculator import SlotCalculator
    all_movies = db.query(Movie).all()
    slot_calc = SlotCalculator(all_movies)
    
    # Group forecasts by date
    forecasts_by_date = defaultdict(list)
    for f in forecasts:
        if "slot" not in f:
            continue
        forecasts_by_date[f["date"]].append(f)
    
    # Pre-allocate prime slots
    prime_allocation = optimizer.allocate_prime_slots(forecasts_by_date, constraint_map)
    
    scheduling_results = []
    scheduled_show_ids = []
    daily_movie_count = defaultdict(lambda: defaultdict(int))
    
    # Schedule by date
    for date_str in sorted(forecasts_by_date.keys()):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        slot_forecasts = forecasts_by_date[date_str]
        
        # Group by slot
        by_slot = defaultdict(list)
        for f in slot_forecasts:
            by_slot[f["slot"]].append(f)
        
        # Process each slot
        for slot in sorted(by_slot.keys()):
            slot_forecasts_sorted = sorted(
                by_slot[slot],
                key=lambda x: x["slot_expected_demand"],
                reverse=True
            )
            
            slot_time = datetime.strptime(slot, "%H:%M").time()
            used_screens = set()
            
            for forecast in slot_forecasts_sorted:
                movie_id = forecast["movie_id"]
                movie_name = forecast["movie"]
                demand = forecast["slot_expected_demand"]
                confidence = forecast.get("confidence", 0.7)
                
                # Check constraints
                constraints = constraint_map.get(movie_name, {})
                max_shows = constraints.get("max_shows_per_day", 999)
                
                if daily_movie_count[date_str][movie_id] >= max_shows:
                    continue
                
                # Check prime slot allocation
                is_prime = slot in PRIME_SLOTS
                if is_prime and (date_str, slot, movie_id) not in prime_allocation:
                    continue
                
                # Select optimal screen
                screen = optimizer.select_optimal_screen(
                    demand, slot, date_str, used_screens
                )
                
                if not screen:
                    continue  # No available screen
                
                # Check conflicts
                if optimizer.check_conflicts(screen.screen_id, date_obj, slot):
                    continue
                
                # Get movie details
                movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
                if not movie:
                    continue
                
                # Use slot calculator for accurate timing
                duration = slot_calc.get_movie_duration(movie_id)
                end_time = slot_calc.calculate_end_time(slot_time, movie_id)
                
                # Verify show can fit
                if not slot_calc.can_fit_show(slot_time, movie_id):
                    continue  # Movie too long for this slot
                
                # Create show
                show = Show(
                    screen_id=screen.screen_id,
                    movie_id=movie_id,
                    show_date=date_obj,
                    show_time=slot_time,
                    end_time=end_time,
                    format=getattr(movie, "format", "2D") or "2D",
                    language=(
                        movie.language[0] if isinstance(movie.language, list) and movie.language
                        else movie.language if movie.language
                        else "English"
                    ),
                    status="UPCOMING"
                )
                db.add(show)
                db.flush()
                
                used_screens.add(screen.screen_id)
                daily_movie_count[date_str][movie_id] += 1
                
                scheduling_results.append({
                    "show_id": show.show_id,
                    "screen": screen.screen_name,
                    "screen_id": screen.screen_id,
                    "movie": movie_name,
                    "movie_id": movie_id,
                    "date": date_str,
                    "time": slot,
                    "slot": slot,
                    "forecast_demand": round(demand, 2),
                    "capacity": optimizer.screen_capacity[screen.screen_id],
                    "confidence": round(confidence, 2),
                    "is_prime_slot": is_prime
                })
                scheduled_show_ids.append(show.show_id)
    
    # Enforce minimum shows
    additional = optimizer.enforce_min_max_shows(
        daily_movie_count, constraint_map, forecasts_by_date
    )
    
    # Schedule additional shows for min constraints
    for add in additional:
        date_str = add["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        slot = add["slot"]
        slot_time = datetime.strptime(slot, "%H:%M").time()
        movie_id = add["movie_id"]
        
        # Find available screen
        for screen in screens:
            if not optimizer.check_conflicts(screen.screen_id, date_obj, slot):
                movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
                if not movie:
                    continue
                
                duration = movie.duration or SLOT_DURATION_MIN
                end_time = (
                    datetime.combine(date_obj, slot_time) +
                    timedelta(minutes=duration)
                ).time()
                
                show = Show(
                    screen_id=screen.screen_id,
                    movie_id=movie_id,
                    show_date=date_obj,
                    show_time=slot_time,
                    end_time=end_time,
                    format=getattr(movie, "format", "2D") or "2D",
                    language=(
                        movie.language[0] if isinstance(movie.language, list) and movie.language
                        else movie.language if movie.language
                        else "English"
                    ),
                    status="UPCOMING"
                )
                db.add(show)
                db.flush()
                
                scheduling_results.append({
                    "show_id": show.show_id,
                    "screen": screen.screen_name,
                    "screen_id": screen.screen_id,
                    "movie": add["movie"],
                    "movie_id": movie_id,
                    "date": date_str,
                    "time": slot,
                    "slot": slot,
                    "forecast_demand": 0,
                    "capacity": optimizer.screen_capacity[screen.screen_id],
                    "confidence": 0.5,
                    "note": "Added for min_shows_per_day constraint"
                })
                scheduled_show_ids.append(show.show_id)
                break
    
    db.commit()
    db.close()
    
    state.setdefault("result", {})
    state["result"]["scheduling"] = scheduling_results
    state["result"]["scheduled_show_ids"] = scheduled_show_ids
    
    prime_count = sum(1 for s in scheduling_results if s.get("is_prime_slot"))
    state["output"] = (
        f"Optimal scheduling: {len(scheduled_show_ids)} shows "
        f"({prime_count} prime slots). Constraints satisfied."
    )
    
    return state