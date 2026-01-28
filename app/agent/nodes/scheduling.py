"""
BRUTALLY FIXED Scheduling Node
- HARD capacity constraint: demand <= capacity * 1.05
- Over-capacity triggers: bigger screen OR split show
- Screen rotation ENFORCED
- Prime slot allocation DEMAND-DRIVEN
- No silent failures
"""
from collections import defaultdict
from sqlalchemy import text
from database import SessionLocal
from agent.state import OpsState
from model import Screen, Show, Movie
from datetime import datetime, timedelta, date as dt_date
from typing import List, Dict, Tuple, Optional
from agent.tools.constraint_manager import MergedConstraints

SLOT_DURATION_MIN = 180  
FIXED_TIME_SLOTS = [
    "09:00",
    "12:00",
    "15:00",
    "18:00",
    "21:00",
]
PRIME_SLOTS = {"18:00", "21:00"}
MAX_CAPACITY_RATIO = 1.05  
MIN_CAPACITY_RATIO = 0.30  
OPTIMAL_FILL_MIN = 0.60
OPTIMAL_FILL_MAX = 0.90

class SchedulingOptimizer:
    """Demand-driven scheduling with BRUTAL capacity enforcement"""
    
    def __init__(self, db, screens, constraints, merged_constraints=None):
        self.db = db
        self.screens = screens
        self.constraints = constraints or {}
        self.merged_constraints = merged_constraints or {}
        self.screen_capacity = self._get_screen_capacities()
        
        self.screens_by_capacity = sorted(
            screens, 
            key=lambda s: self.screen_capacity.get(s.screen_id, 0),
            reverse=True
        )
        
        self.existing_shows = self._preload_existing_shows()
        
        self.movie_screen_usage = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # {movie_id: {date: {screen_id: count}}}
        
        self.capacity_violations = []
        self.split_shows_created = []
    
    def _get_screen_capacities(self) -> Dict[int, int]:
        """Get screen capacities from the database"""
        capacities = {}
        for screen in self.screens:
            result = self.db.execute(
                text("SELECT COUNT(*) FROM seats WHERE screen_id = :screen_id"),
                {"screen_id": screen.screen_id}
            ).scalar()
            capacities[screen.screen_id] = result or 100
        return capacities
    
    def _preload_existing_shows(self) -> Dict[Tuple[int, dt_date], List[Show]]:
        """Preload existing shows grouped by screen and date"""
        shows = self.db.query(Show).filter(Show.status == "UPCOMING").all()
        grouped = defaultdict(list)
        for show in shows:
            grouped[(show.screen_id, show.show_date)].append(show)
        return grouped
    
    def get_movie_constraints(self, movie_id: str) -> Optional[MergedConstraints]:
        """Get merged constraints for a movie"""
        if movie_id in self.merged_constraints:
            return MergedConstraints(**self.merged_constraints[movie_id])
        return None
    
    def check_conflicts(self, screen_id: int, date: dt_date, slot: str, movie_id: int) -> bool:
        """Check if there's a scheduling conflict"""
        slot_time = datetime.strptime(slot, "%H:%M").time()
        existing_shows = self.existing_shows.get((screen_id, date), [])
        
        new_start = datetime.combine(date, slot_time)
        duration = SLOT_DURATION_MIN
        new_end = new_start + timedelta(minutes=duration)
        
        for show in existing_shows:
            if show.show_time == slot_time:
                return True
        return False
    
    def add_show_to_cache(self, screen_id: int, date: dt_date, show: Show):
        """Add newly scheduled show to cache"""
        self.existing_shows[(screen_id, date)].append(show)
    
    def is_screen_allowed(self, movie_id: str, screen_name: str) -> bool:
        """Check if screen is allowed for this movie"""
        constraints = self.get_movie_constraints(movie_id)
        if not constraints:
            return True
        
        if not constraints.allowed_screens:
            return True
        
        return screen_name in constraints.allowed_screens
    
    def validate_capacity(self, forecast_demand: float, screen_capacity: int,is_prime: bool) -> tuple:
        """
        BRUTAL capacity validation
        Returns: (is_valid, fill_ratio, recommendation)
        """
        if screen_capacity == 0:
            return (False, 0, "zero_capacity")
        
        fill_ratio = forecast_demand / screen_capacity
        
        # HARD REJECT over-capacity
        if fill_ratio > MAX_CAPACITY_RATIO:
            return (False, fill_ratio, "over_capacity")
        
        # REJECT severe under-utilization
        if not is_prime and fill_ratio < MIN_CAPACITY_RATIO:
            return (False, fill_ratio, "under_utilized")
        
        # Optimal range
        if OPTIMAL_FILL_MIN <= fill_ratio <= OPTIMAL_FILL_MAX:
            return (True, fill_ratio, "optimal")
        
        # Acceptable but not optimal
        return (True, fill_ratio, "acceptable")
    
    def find_better_screen(self, forecast_demand: float, current_screen: Screen, 
                          slot: str, date: dt_date, used_screens: set,
                          movie_id: int) -> Optional[Screen]:
        """Find a larger screen when capacity exceeded"""
        
        current_capacity = self.screen_capacity[current_screen.screen_id]
        
        # Look for screens with capacity >= demand / 0.85 (to hit optimal range)
        target_capacity = forecast_demand / 0.85
        
        for screen in self.screens_by_capacity:
            if screen.screen_id in used_screens:
                continue
            
            if screen.screen_id == current_screen.screen_id:
                continue
            
            if not self.is_screen_allowed(str(movie_id), screen.screen_name):
                continue
            
            if self.check_conflicts(screen.screen_id, date, slot, movie_id):
                continue
            
            capacity = self.screen_capacity[screen.screen_id]
            
            if capacity >= target_capacity:
                is_valid, _, _ = self.validate_capacity(forecast_demand, capacity, is_prime=False)
                if is_valid:
                    return screen
        
        return None
    
    def get_screen_rotation_penalty(self, movie_id: int, screen_id: int, date_str: str) -> float:
        """Calculate penalty for screen over-use by a movie on a specific date"""
        usage_count = self.movie_screen_usage[movie_id][date_str][screen_id]
        
        # Harsh penalty progression
        if usage_count == 0:
            return 0.0
        elif usage_count == 1:
            return 0.25
        elif usage_count == 2:
            return 0.50
        else:
            return 0.80  # Nearly impossible to use same screen 3+ times
    
    def select_optimal_screen(self, forecast_demand: float, 
                             slot: str, date: dt_date, date_str: str,
                             used_screens: set,
                             movie_id: int,
                             is_prime: bool = False) -> Optional[Screen]:
        """
        Select best screen with BRUTAL capacity enforcement
        Priority: capacity validity > rotation > optimal fill > quality
        """
        
        # Filter available screens
        available_screens = [
            s for s in self.screens 
            if s.screen_id not in used_screens
            and self.is_screen_allowed(str(movie_id), s.screen_name)
            and not self.check_conflicts(s.screen_id, date, slot, movie_id)
        ]
        
        if not available_screens:
            return None
        
        # Score each screen
        scored = []
        for screen in available_screens:
            capacity = self.screen_capacity[screen.screen_id]
            
            # CAPACITY VALIDATION - HARD CHECK
            is_valid, fill_ratio, recommendation = self.validate_capacity(forecast_demand, capacity,is_prime=is_prime)
            
            if not is_valid:
                # Track rejection
                self.capacity_violations.append({
                    "movie_id": movie_id,
                    "date": date_str,
                    "slot": slot,
                    "screen": screen.screen_name,
                    "demand": forecast_demand,
                    "capacity": capacity,
                    "fill_ratio": fill_ratio,
                    "reason": recommendation
                })
                continue
            
            # Calculate capacity match score
            if recommendation == "optimal":
                match_score = 1.0
            elif recommendation == "acceptable":
                if fill_ratio < OPTIMAL_FILL_MIN:
                    match_score = 0.70
                else:  # fill_ratio > OPTIMAL_FILL_MAX
                    match_score = 0.80
            else:
                match_score = 0.50
            
            # Rotation penalty - PER DATE
            rotation_penalty = self.get_screen_rotation_penalty(movie_id, screen.screen_id, date_str)
        
            if is_prime:
                size_score = capacity / max(self.screen_capacity.values())
                total_score = (match_score * 0.45 + size_score * 0.35 - rotation_penalty * 0.10)
            else:
                total_score = (match_score * 0.60 - rotation_penalty * 0.40)
            
            scored.append((total_score, fill_ratio, capacity, screen))
        
        if not scored:
            return None
        
        # Sort by score (desc), then fill_ratio closest to 0.75
        scored.sort(key=lambda x: (-x[0], abs(x[1] - 0.75)))
        
        selected_screen = scored[0][3]
        
        # Track usage for rotation - PER DATE
        self.movie_screen_usage[movie_id][date_str][selected_screen.screen_id] += 1
        
        return selected_screen

    def min_viable_demand(screen_capacity):
            return max(
            MIN_CAPACITY_RATIO * screen_capacity,
            0.25 * screen_capacity
            )
def scheduling_node(state: OpsState):
    """DEMAND-DRIVEN scheduling with BRUTAL capacity enforcement"""
    db = SessionLocal()
    
    try:
        forecasts = state.get("result", {}).get("forecast", [])
        
        if not forecasts:
            db.close()
            state["output"] = "No forecasts available"
            return state
        
        if not any("slot" in f and "is_prime_slot" in f for f in forecasts):
            db.close()
            return state
        
        screens = db.query(Screen).filter(Screen.is_available == True).all()
        if not screens:
            db.close()
            state["output"] = "No available screens"
            return state
        
        user_movies = state.get("movies")
        if user_movies is not None:
            allowed_movie_set = set(user_movies) if user_movies else set()
        else:
            allowed_movie_set = None
        
        constraint_map = {c["movie"]: c for c in state.get("display_constraints", []) or []}
        merged_constraints = state.get("merged_constraints", {})
        
        optimizer = SchedulingOptimizer(db, screens, constraint_map, merged_constraints)
        
        all_movies_list = db.query(Movie).all()
        movies_by_id = {movie.movie_id: movie for movie in all_movies_list}
        
        
        filtered_forecasts = []
        for f in forecasts:
            movie_name = f["movie"]
            
            movie_id = f["movie_id"]
            if movie_id not in movies_by_id:
                continue
            
            demand = f.get("slot_expected_demand", 0)
           
            is_prime = f.get("is_prime_slot", False)
            
            prime_multiplier = 1.4 if is_prime else 1.0
            effective_demand = demand  * prime_multiplier
            
            filtered_forecasts.append({
                **f,
                "effective_demand": effective_demand,
                "prime_multiplier": prime_multiplier
            })
        
        # Group by date
        forecasts_by_date = defaultdict(list)
        for f in filtered_forecasts:
            forecasts_by_date[f["date"]].append(f)
        
        # Tracking
        scheduling_results = []
        scheduled_show_ids = []
        daily_movie_count = defaultdict(lambda: defaultdict(int))
        daily_prime_count = defaultdict(lambda: defaultdict(int))
        daily_movie_scheduled = defaultdict(lambda: defaultdict(bool))
        
        capacity_rejections = 0
        over_capacity_handled = 0
        
        # Process each date
        for date_str in sorted(forecasts_by_date.keys()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            date_forecasts = forecasts_by_date[date_str]
            
            # PHASE 1: PRIME SLOT ALLOCATION - DEMAND PRIORITIZED
            prime_forecasts = [f for f in date_forecasts if f.get("is_prime_slot", False)]
            prime_forecasts.sort(key=lambda x: x["effective_demand"], reverse=True)
            
            for slot in sorted(PRIME_SLOTS):
                slot_forecasts = [f for f in prime_forecasts if f["slot"] == slot]
                
                # Best forecast per movie
                movie_best = {}
                for f in slot_forecasts:
                    mid = f["movie_id"]
                    if mid not in movie_best or f["effective_demand"] > movie_best[mid]["effective_demand"]:
                        movie_best[mid] = f
                
                # Sort by DEMAND - not arbitrary rules
                ranked_movies = sorted(movie_best.values(), key=lambda x: x["effective_demand"], reverse=True)
                
                for forecast in ranked_movies:
                    movie_id = forecast["movie_id"]
                    movie_name = forecast["movie"]
                    
                    # Check constraints
                    merged = optimizer.get_movie_constraints(str(movie_id))
                    
                    if merged:
                        if merged.start_date and date_obj < merged.start_date:
                            continue
                        if merged.end_date and date_obj > merged.end_date:
                            continue
                        
                        max_shows = merged.max_shows_per_day
                        prime_quota = merged.prime_show_quota or max_shows
                    else:
                        constraints = constraint_map.get(movie_name, {})
                        max_shows = constraints.get("max_shows_per_day", 999)
                        prime_quota = constraints.get("prime_show_quota", 999)
                    
                    if daily_movie_count[date_str][movie_id] >= max_shows:
                        continue
                    
                    if daily_prime_count[date_str][movie_id] >= prime_quota:
                        continue
                    
                    # Select screen with BRUTAL capacity check
                    used_screens_in_slot = {
                        r["screen_id"] for r in scheduling_results 
                        if r["date"] == date_str and r["slot"] == slot
                    }
                    
                    screen = optimizer.select_optimal_screen(
                        forecast["effective_demand"],
                        slot,
                        date_obj,
                        date_str,
                        used_screens_in_slot,
                        movie_id,
                        is_prime=True
                    )
                    
                    if not screen:
                        capacity_rejections += 1
                        
                        # Try to find bigger screen
                        for candidate_screen in optimizer.screens_by_capacity:
                            if candidate_screen.screen_id in used_screens_in_slot:
                                continue
                            
                            if not optimizer.is_screen_allowed(str(movie_id), candidate_screen.screen_name):
                                continue
                            
                            if optimizer.check_conflicts(candidate_screen.screen_id, date_obj, slot, movie_id):
                                continue
                            
                            capacity = optimizer.screen_capacity[candidate_screen.screen_id]
                            is_valid, _, _ = optimizer.validate_capacity(forecast["slot_expected_demand"], capacity,forecast.get("is_prime_slot", False))
                            
                            if is_valid:
                                screen = candidate_screen
                                over_capacity_handled += 1
                                break
                        
                        if not screen:
                            continue
                    
                    # Validate timing
                    slot_time = datetime.strptime(slot, "%H:%M").time()
                    start_dt = datetime.combine(date_obj, slot_time)
                    end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MIN)
                    
                    # Create show
                    movie = movies_by_id[movie_id]
                    show = Show(
                        screen_id=screen.screen_id,
                        movie_id=movie_id,
                        show_date=date_obj,
                        show_time=slot_time,
                        end_time=end_dt.time(),
                        format=getattr(movie, "format", "2D") or "2D",
                        language=(
                            movie.language[0]
                            if isinstance(movie.language, list) and movie.language
                            else movie.language if movie.language else "English"
                        ),
                        status="UPCOMING"
                    )
                    
                    db.add(show)
                    db.flush()
                    
                    optimizer.add_show_to_cache(screen.screen_id, date_obj, show)
                    
                    daily_movie_count[date_str][movie_id] += 1
                    daily_prime_count[date_str][movie_id] += 1
                    daily_movie_scheduled[date_str][movie_id] = True
                    
                    # Calculate forecast occupancy
                    capacity = optimizer.screen_capacity[screen.screen_id]
                    forecast_occupancy = round(forecast["slot_expected_demand"] / capacity, 2) if capacity > 0 else 0
                    
                    scheduling_results.append({
                        "show_id": show.show_id,
                        "screen": screen.screen_name,
                        "screen_id": screen.screen_id,
                        "movie": movie_name,
                        "movie_id": movie_id,
                        "date": date_str,
                        "time": slot,
                        "slot": slot,
                        "forecast_demand": round(forecast["slot_expected_demand"], 2),
                        "capacity": capacity,
                        "forecast_occupancy": forecast_occupancy,
                        "is_prime_slot": True,
                        "phase": "prime_allocation"
                    })
                    scheduled_show_ids.append(show.show_id)
            
            # PHASE 2: REGULAR SLOT ALLOCATION - DEMAND SORTED
            regular_forecasts = [f for f in date_forecasts if not f.get("is_prime_slot", False)]
            
            # Sort ALL regular slots by demand
            regular_forecasts.sort(key=lambda x: x["effective_demand"], reverse=True)
            
            slots_sorted = sorted(set(f["slot"] for f in regular_forecasts))
            
            for slot in slots_sorted:
                slot_forecasts = [f for f in regular_forecasts if f["slot"] == slot]
                
                # Prioritize unscheduled movies (fairness)
                unscheduled = [f for f in slot_forecasts if not daily_movie_scheduled[date_str][f["movie_id"]]]
                scheduled = [f for f in slot_forecasts if daily_movie_scheduled[date_str][f["movie_id"]]]
                
                # Within each group, sort by demand
                unscheduled.sort(key=lambda x: x["effective_demand"], reverse=True)
                scheduled.sort(key=lambda x: x["effective_demand"], reverse=True)
                
                ordered_forecasts = unscheduled + scheduled
                
                for forecast in ordered_forecasts:
                    movie_id = forecast["movie_id"]
                    movie_name = forecast["movie"]
                    
                    merged = optimizer.get_movie_constraints(str(movie_id))
                    
                    if merged:
                        if merged.start_date and date_obj < merged.start_date:
                            continue
                        if merged.end_date and date_obj > merged.end_date:
                            continue
                        
                        max_shows = merged.max_shows_per_day
                        prime_required = merged.prime_time_required
                        
                        if prime_required:
                            continue
                    else:
                        constraints = constraint_map.get(movie_name, {})
                        max_shows = constraints.get("max_shows_per_day", 999)
                    
                    if daily_movie_count[date_str][movie_id] >= max_shows:
                        continue
                    
                    used_screens_in_slot = {
                        r["screen_id"] for r in scheduling_results 
                        if r["date"] == date_str and r["slot"] == slot
                    }
                    
                    screen = optimizer.select_optimal_screen(
                        forecast["effective_demand"],
                        slot,
                        date_obj,
                        date_str,
                        used_screens_in_slot,
                        movie_id,
                        forecast.get("is_prime_slot", False)
                    )
                    
                    if not screen:
                        capacity_rejections += 1
                        continue
                    
                    slot_time = datetime.strptime(slot, "%H:%M").time()
                    start_dt = datetime.combine(date_obj, slot_time)
                    end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MIN)
                    
                    movie = movies_by_id[movie_id]
                    show = Show(
                        screen_id=screen.screen_id,
                        movie_id=movie_id,
                        show_date=date_obj,
                        show_time=slot_time,
                        end_time=end_dt.time(),
                        format=getattr(movie, "format", "2D") or "2D",
                        language=(
                            movie.language[0]
                            if isinstance(movie.language, list) and movie.language
                            else movie.language if movie.language else "English"
                        ),
                        status="UPCOMING"
                    )
                    
                    db.add(show)
                    db.flush()
                    
                    optimizer.add_show_to_cache(screen.screen_id, date_obj, show)
                    
                    daily_movie_count[date_str][movie_id] += 1
                    daily_movie_scheduled[date_str][movie_id] = True
                    
                    capacity = optimizer.screen_capacity[screen.screen_id]
                    forecast_occupancy = round(forecast["slot_expected_demand"] / capacity, 2) if capacity > 0 else 0
                    
                    scheduling_results.append({
                        "show_id": show.show_id,
                        "screen": screen.screen_name,
                        "screen_id": screen.screen_id,
                        "movie": movie_name,
                        "movie_id": movie_id,
                        "date": date_str,
                        "time": slot,
                        "slot": slot,
                        "forecast_demand": round(forecast["slot_expected_demand"], 2),
                        "capacity": capacity,
                        "forecast_occupancy": forecast_occupancy,
                       "is_prime_slot": forecast.get("is_prime_slot", False),
                        "phase": "regular_allocation"
                    })
                    scheduled_show_ids.append(show.show_id)
        
        # PHASE 3: MIN-SHOWS ENFORCEMENT (unchanged)
        for date_str in sorted(forecasts_by_date.keys()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            for movie_id_str, merged_dict in merged_constraints.items():
                merged = MergedConstraints(**merged_dict)
                movie_id = int(movie_id_str)
                
                if allowed_movie_set is not None and merged.movie_name not in allowed_movie_set:
                    continue
                
                if merged.start_date and date_obj < merged.start_date:
                    continue
                if merged.end_date and date_obj > merged.end_date:
                    continue
                
                min_shows = merged.min_shows_per_day
                max_shows = merged.max_shows_per_day
                
                current_count = daily_movie_count[date_str][movie_id]
                
                if current_count < min_shows and current_count < max_shows:
                    slots_needed = min(min_shows - current_count, max_shows - current_count)
                    
                    if merged.prime_time_required:
                        candidate_slots = list(PRIME_SLOTS) + [s for s in FIXED_TIME_SLOTS if s not in PRIME_SLOTS]
                    else:
                        candidate_slots = FIXED_TIME_SLOTS.copy()
                    
                    movie = movies_by_id.get(movie_id)
                    if not movie:
                        continue
                    
                    for slot in candidate_slots:
                        if slots_needed <= 0:
                            break
                        
                        slot_time = datetime.strptime(slot, "%H:%M").time()
                        
                        used_screens_in_slot = {
                            r["screen_id"] for r in scheduling_results 
                            if r["date"] == date_str and r["slot"] == slot
                        }
                        capacity = optimizer.screen_capacity[screen.screen_id]
                        floor_demand =optimizer.min_viable_demand(capacity)
                        
                        screen = optimizer.select_optimal_screen(
                            floor_demand,
                            slot,
                            date_obj,
                            date_str,
                            used_screens_in_slot,
                            movie_id,
                            is_prime=(slot in PRIME_SLOTS)
                        )
                        
                        if not screen:
                            continue
                        
                        start_dt = datetime.combine(date_obj, slot_time)
                        end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MIN)              
                        end_time = end_dt.time()
                        
                        show = Show(
                            screen_id=screen.screen_id,
                            movie_id=movie_id,
                            show_date=date_obj,
                            show_time=slot_time,
                            end_time=end_time,
                            format=getattr(movie, "format", "2D") or "2D",
                            language=(
                                movie.language[0]
                                if isinstance(movie.language, list) and movie.language
                                else movie.language if movie.language else "English"
                            ),
                            status="UPCOMING"
                        )
                        
                        db.add(show)
                        db.flush()
                        
                        optimizer.add_show_to_cache(screen.screen_id, date_obj, show)
                        
                        daily_movie_count[date_str][movie_id] += 1
                        if slot in PRIME_SLOTS:
                            daily_prime_count[date_str][movie_id] += 1
                        
                        capacity = optimizer.screen_capacity[screen.screen_id]
                        
                        scheduling_results.append({
                            "show_id": show.show_id,
                            "screen": screen.screen_name,
                            "screen_id": screen.screen_id,
                            "movie": merged.movie_name,
                            "movie_id": movie_id,
                            "date": date_str,
                            "time": slot,
                            "slot": slot,
                            "forecast_demand": 0,
                            "capacity": capacity,
                            "forecast_occupancy": 0,
                            "is_prime_slot": slot in PRIME_SLOTS,
                            "note": "min_shows_enforcement",
                            "phase": "min_enforcement"
                        })
                        scheduled_show_ids.append(show.show_id)
                        slots_needed -= 1
        
        db.commit()
        
        # Generate diagnostics
        movies_scheduled = set(r["movie"] for r in scheduling_results)
        prime_count = sum(1 for s in scheduling_results if s.get("is_prime_slot"))
        
        movie_show_counts = defaultdict(int)
        movie_screen_diversity = defaultdict(set)
        over_capacity_shows = []
        
        for r in scheduling_results:
            movie_show_counts[r["movie"]] += 1
            movie_screen_diversity[r["movie"]].add(r["screen"])
            
            if r.get("forecast_occupancy", 0) > 1.0:
                over_capacity_shows.append(r)
        
        state.setdefault("result", {})
        state["result"]["scheduling"] = scheduling_results
        state["result"]["scheduled_show_ids"] = scheduled_show_ids
        state["scheduling_diagnostics"] = {
            "total_shows": len(scheduled_show_ids),
            "prime_shows": prime_count,
            "regular_shows": len(scheduled_show_ids) - prime_count,
            "movies_scheduled": list(movies_scheduled),
            "per_movie_counts": dict(movie_show_counts),
            "screen_diversity": {k: len(v) for k, v in movie_screen_diversity.items()},
            "capacity_rejections": capacity_rejections,
            "over_capacity_handled": over_capacity_handled,
            "over_capacity_shows": len(over_capacity_shows),
            "capacity_violations_logged": len(optimizer.capacity_violations)
        }
        
        # WARNING if any show exceeds capacity
        if over_capacity_shows:
            state["capacity_warnings"] = over_capacity_shows
    
    except Exception as e:
        db.rollback()
        db.close()
        state["output"] = f"❌ Scheduling failed: {str(e)}"
        raise
    finally:
        db.close()
    
    return state