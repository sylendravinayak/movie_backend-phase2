"""
REWRITTEN Scheduling Node - Clear, Debuggable, Robust
Key improvements:
- Explicit validation at each step
- Clear logging of why forecasts are skipped
- Simplified screen selection logic
- Better error messages
"""
from collections import defaultdict
from sqlalchemy import text
from database import SessionLocal
from agent.state import OpsState
from model import Screen, Show, Movie
from datetime import datetime, timedelta, date as dt_date
from typing import List, Dict, Tuple, Optional
from agent.tools.constraint_manager import MergedConstraints

# Constants
SLOT_DURATION_MIN = 180  
FIXED_TIME_SLOTS = ["09:00", "12:00", "15:00", "18:00", "21:00"]
PRIME_SLOTS = {"18:00", "21:00"}
MAX_CAPACITY_RATIO = 1.05
MIN_CAPACITY_RATIO = 0.30
OPTIMAL_FILL_MIN = 0.60
OPTIMAL_FILL_MAX = 0.90


class SchedulingDebugger:
    """Track why forecasts are being skipped"""
    
    def __init__(self):
        self.skipped_forecasts = []
        self.capacity_issues = []
        self.constraint_blocks = []
        self.successful_schedules = []
    
    def log_skip(self, forecast: dict, reason: str, details: dict = None):
        """Log a skipped forecast"""
        self.skipped_forecasts.append({
            "movie": forecast.get("movie"),
            "date": forecast.get("date"),
            "slot": forecast.get("slot"),
            "demand": forecast.get("slot_expected_demand"),
            "reason": reason,
            "details": details or {}
        })
    
    def log_capacity_issue(self, movie: str, date: str, slot: str, 
                          demand: float, capacity: int, reason: str):
        """Log capacity-related issues"""
        self.capacity_issues.append({
            "movie": movie,
            "date": date,
            "slot": slot,
            "demand": demand,
            "capacity": capacity,
            "fill_ratio": demand / capacity if capacity > 0 else 0,
            "reason": reason
        })
    
    def log_success(self, forecast: dict, screen: Screen, phase: str):
        """Log successful scheduling"""
        self.successful_schedules.append({
            "movie": forecast.get("movie"),
            "date": forecast.get("date"),
            "slot": forecast.get("slot"),
            "screen": screen.screen_name,
            "phase": phase
        })
    
    def print_summary(self):
        """Print debugging summary"""
        print("\n" + "="*80)
        print("SCHEDULING DEBUG SUMMARY")
        print("="*80)
        
        print(f"\n✅ Successful schedules: {len(self.successful_schedules)}")
        if self.successful_schedules:
            by_phase = defaultdict(int)
            for s in self.successful_schedules:
                by_phase[s['phase']] += 1
            for phase, count in by_phase.items():
                print(f"   - {phase}: {count}")
        
        print(f"\n⚠️  Skipped forecasts: {len(self.skipped_forecasts)}")
        if self.skipped_forecasts:
            by_reason = defaultdict(int)
            for s in self.skipped_forecasts:
                by_reason[s['reason']] += 1
            for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
                print(f"   - {reason}: {count}")
        
        print(f"\n🚫 Capacity issues: {len(self.capacity_issues)}")
        if self.capacity_issues:
            by_reason = defaultdict(int)
            for c in self.capacity_issues:
                by_reason[c['reason']] += 1
            for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
                print(f"   - {reason}: {count}")
        
        print("\n" + "="*80 + "\n")


class ImprovedSchedulingOptimizer:
    """Simplified, clearer scheduling optimizer"""
    
    def __init__(self, db, screens, constraints, merged_constraints=None):
        self.db = db
        self.screens = screens
        self.constraints = constraints or {}
        self.merged_constraints = merged_constraints or {}
        self.screen_capacity = self._get_screen_capacities()
        self.existing_shows = self._preload_existing_shows()
        self.debugger = SchedulingDebugger()
        
        # Track usage
        self.daily_movie_count = defaultdict(lambda: defaultdict(int))
        self.daily_prime_count = defaultdict(lambda: defaultdict(int))
        self.slot_screen_usage = defaultdict(set)  # (date, slot) -> {screen_ids}
    
    def _get_screen_capacities(self) -> Dict[int, int]:
        """Get screen capacities"""
        capacities = {}
        for screen in self.screens:
            result = self.db.execute(
                text("SELECT COUNT(*) FROM seats WHERE screen_id = :screen_id"),
                {"screen_id": screen.screen_id}
            ).scalar()
            capacities[screen.screen_id] = result or 100
        return capacities
    
    def _preload_existing_shows(self) -> Dict[Tuple[int, dt_date, str], Show]:
        """Preload existing shows indexed by (screen_id, date, slot)"""
        shows = self.db.query(Show).filter(Show.status == "UPCOMING").all()
        indexed = {}
        for show in shows:
            slot = show.show_time.strftime("%H:%M")
            key = (show.screen_id, show.show_date, slot)
            indexed[key] = show
        return indexed
    
    def is_slot_occupied(self, screen_id: int, date: dt_date, slot: str) -> bool:
        """Check if a slot is already occupied"""
        key = (screen_id, date, slot)
        return key in self.existing_shows
    
    def get_movie_constraints(self, movie_id: int) -> Optional[MergedConstraints]:
        """Get merged constraints for a movie"""
        movie_id_str = str(movie_id)
        if movie_id_str in self.merged_constraints:
            return MergedConstraints(**self.merged_constraints[movie_id_str])
        return None
    
    def check_date_constraints(self, movie_id: int, date: dt_date) -> Tuple[bool, str]:
        """Check if date is valid for this movie"""
        constraints = self.get_movie_constraints(movie_id)
        if not constraints:
            return True, "no_constraints"
        
        if constraints.start_date and date < constraints.start_date:
            return False, f"before_start_date_{constraints.start_date}"
        
        if constraints.end_date and date > constraints.end_date:
            return False, f"after_end_date_{constraints.end_date}"
        
        return True, "valid"
    
    def check_daily_quota(self, movie_id: int, date_str: str, is_prime: bool) -> Tuple[bool, str]:
        """Check if movie has reached its daily quota"""
        constraints = self.get_movie_constraints(movie_id)
        
        current_total = self.daily_movie_count[date_str][movie_id]
        current_prime = self.daily_prime_count[date_str][movie_id]
        
        if constraints:
            max_shows = constraints.max_shows_per_day
            prime_quota = constraints.prime_show_quota or max_shows
            
            if current_total >= max_shows:
                return False, f"max_shows_reached_{current_total}/{max_shows}"
            
            if is_prime and current_prime >= prime_quota:
                return False, f"prime_quota_reached_{current_prime}/{prime_quota}"
        
        return True, "quota_ok"
    
    def check_screen_allowed(self, movie_id: int, screen_name: str) -> Tuple[bool, str]:
        """Check if screen is allowed for this movie"""
        constraints = self.get_movie_constraints(movie_id)
        if not constraints or not constraints.allowed_screens:
            return True, "no_screen_restrictions"
        
        if screen_name in constraints.allowed_screens:
            return True, "screen_allowed"
        
        return False, f"screen_not_in_allowed_list"
    
    def validate_capacity(self, demand: float, capacity: int, is_prime: bool) -> Tuple[bool, float, str]:
        """
        Validate if demand fits capacity
        Returns: (is_valid, fill_ratio, reason)
        """
        if capacity == 0:
            return False, 0, "zero_capacity"
        
        fill_ratio = demand / capacity
        
        # Hard reject over-capacity
        if fill_ratio > MAX_CAPACITY_RATIO:
            return False, fill_ratio, "over_capacity"
        
        # Reject severe under-utilization (except prime slots which need flexibility)
        if not is_prime and fill_ratio < MIN_CAPACITY_RATIO:
            return False, fill_ratio, "under_utilized"
        
        # Optimal range
        if OPTIMAL_FILL_MIN <= fill_ratio <= OPTIMAL_FILL_MAX:
            return True, fill_ratio, "optimal"
        
        # Acceptable but not optimal
        return True, fill_ratio, "acceptable"
    
    def find_best_screen(self, forecast: dict, date: dt_date, 
                        allowed_movie_set: Optional[set] = None) -> Optional[Screen]:
        """
        Find the best available screen for a forecast
        Returns None if no suitable screen found
        """
        movie_id = forecast["movie_id"]
        movie_name = forecast["movie"]
        slot = forecast["slot"]
        date_str = forecast["date"]
        demand = forecast.get("slot_expected_demand", 0)
        is_prime = forecast.get("is_prime_slot", False)
        
        # Check if movie is in allowed set
        if allowed_movie_set is not None and movie_name not in allowed_movie_set:
            self.debugger.log_skip(forecast, "movie_not_in_allowed_set")
            return None
        
        # Check date constraints
        date_valid, date_reason = self.check_date_constraints(movie_id, date)
        if not date_valid:
            self.debugger.log_skip(forecast, "date_constraint", {"reason": date_reason})
            return None
        
        # Check daily quota
        quota_ok, quota_reason = self.check_daily_quota(movie_id, date_str, is_prime)
        if not quota_ok:
            self.debugger.log_skip(forecast, "quota_exceeded", {"reason": quota_reason})
            return None
        
        # Get screens already used in this slot
        used_screens = self.slot_screen_usage[(date_str, slot)]
        
        # Find available screens
        available_screens = []
        for screen in self.screens:
            # Skip if already used in this slot
            if screen.screen_id in used_screens:
                continue
            
            # Check if slot is occupied
            if self.is_slot_occupied(screen.screen_id, date, slot):
                continue
            
            # Check screen restrictions
            screen_ok, screen_reason = self.check_screen_allowed(movie_id, screen.screen_name)
            if not screen_ok:
                continue
            
            # Check capacity
            capacity = self.screen_capacity[screen.screen_id]
            valid, fill_ratio, cap_reason = self.validate_capacity(demand, capacity, is_prime)
            
            if not valid:
                self.debugger.log_capacity_issue(
                    movie_name, date_str, slot, demand, capacity, cap_reason
                )
                continue
            
            # Screen is valid - add with score
            score = self._score_screen(screen, demand, capacity, fill_ratio, is_prime, 
                                      movie_id, date_str)
            available_screens.append((score, fill_ratio, screen))
        
        if not available_screens:
            self.debugger.log_skip(forecast, "no_available_screens", {
                "used_screens": len(used_screens),
                "total_screens": len(self.screens)
            })
            return None
        
        # Sort by score (descending), then fill_ratio closest to 0.75
        available_screens.sort(key=lambda x: (-x[0], abs(x[1] - 0.75)))
        
        return available_screens[0][2]
    
    def _score_screen(self, screen: Screen, demand: float, capacity: int,
                     fill_ratio: float, is_prime: bool, movie_id: int, 
                     date_str: str) -> float:
        """Score a screen for selection"""
        score = 0.0
        
        # Capacity match score
        if OPTIMAL_FILL_MIN <= fill_ratio <= OPTIMAL_FILL_MAX:
            score += 1.0  # Optimal
        elif fill_ratio < OPTIMAL_FILL_MIN:
            score += 0.6  # Under-utilized
        else:
            score += 0.8  # Slightly over
        
        # Prime slot bonus - prefer larger screens
        if is_prime:
            max_capacity = max(self.screen_capacity.values())
            size_score = capacity / max_capacity
            score += size_score * 0.5
        
        # Penalize screen reuse by same movie on same date
        # (Not same slot, but same date to encourage rotation)
        movie_screens_today = set()
        for other_date_str, counts in self.daily_movie_count.items():
            if other_date_str == date_str and movie_id in counts:
                # Check which screens this movie used today
                for (d, s), screen_ids in self.slot_screen_usage.items():
                    if d == date_str and screen.screen_id in screen_ids:
                        # This screen was already used by this movie today
                        score -= 0.2
                        break
        
        return score
    
    def schedule_show(self, forecast: dict, screen: Screen, 
                     movies_by_id: Dict[int, Movie], phase: str) -> Optional[Show]:
        """Create and persist a show"""
        movie_id = forecast["movie_id"]
        date_str = forecast["date"]
        slot = forecast["slot"]
        is_prime = forecast.get("is_prime_slot", False)
        
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        slot_time = datetime.strptime(slot, "%H:%M").time()
        
        start_dt = datetime.combine(date_obj, slot_time)
        end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MIN)
        
        movie = movies_by_id.get(movie_id)
        if not movie:
            return None
        
        # Create show
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
        
        self.db.add(show)
        self.db.flush()
        
        # Update tracking
        key = (screen.screen_id, date_obj, slot)
        self.existing_shows[key] = show
        
        self.slot_screen_usage[(date_str, slot)].add(screen.screen_id)
        self.daily_movie_count[date_str][movie_id] += 1
        if is_prime:
            self.daily_prime_count[date_str][movie_id] += 1
        
        # Log success
        self.debugger.log_success(forecast, screen, phase)
        
        return show


def scheduling_node(state: OpsState):
    """
    REWRITTEN scheduling node - clear and debuggable
    """
    print("\n" + "="*80)
    print("SCHEDULING NODE START")
    print("="*80)
    
    db = SessionLocal()
    
    try:
        # 1. VALIDATE INPUT
        forecasts = state.get("result", {}).get("forecast", [])
        
        print(f"\n📊 Input validation:")
        print(f"   - Total forecasts: {len(forecasts)}")
        
        if not forecasts:
            print("   ❌ No forecasts available")
            db.close()
            state["output"] = "No forecasts available for scheduling"
            return state
        
        # Check if forecasts have slot-level data
        slot_level_forecasts = [f for f in forecasts if "slot" in f and "is_prime_slot" in f]
        print(f"   - Slot-level forecasts: {len(slot_level_forecasts)}")
        
        if not slot_level_forecasts:
            print("   ❌ Forecasts are not at slot level")
            db.close()
            return state
        
        # 2. LOAD RESOURCES
        screens = db.query(Screen).filter(Screen.is_available == True).all()
        print(f"\n🎬 Available screens: {len(screens)}")
        
        if not screens:
            print("   ❌ No available screens")
            db.close()
            state["output"] = "No available screens"
            return state
        
        for screen in screens:
            capacity = db.execute(
                text("SELECT COUNT(*) FROM seats WHERE screen_id = :sid"),
                {"sid": screen.screen_id}
            ).scalar()
            print(f"   - {screen.screen_name}: {capacity} seats")
        
        # 3. LOAD MOVIES
        all_movies = db.query(Movie).all()
        movies_by_id = {m.movie_id: m for m in all_movies}
        print(f"\n🎥 Total movies in database: {len(movies_by_id)}")
        
        # 4. FILTER BY ALLOWED MOVIES
        user_movies = state.get("movies")
        if user_movies is not None and len(user_movies) > 0:
            allowed_movie_set = set(user_movies)
            print(f"   - User requested movies: {len(allowed_movie_set)}")
            print(f"   - Movies: {', '.join(sorted(allowed_movie_set))}")
        else:
            allowed_movie_set = None
            print(f"   - No movie filter - scheduling all movies")
        
        # 5. INITIALIZE OPTIMIZER
        constraint_map = {c["movie"]: c for c in state.get("display_constraints", []) or []}
        merged_constraints = state.get("merged_constraints", {})
        
        print(f"\n⚙️  Constraints:")
        print(f"   - User constraints: {len(constraint_map)}")
        print(f"   - Merged constraints: {len(merged_constraints)}")
        
        optimizer = ImprovedSchedulingOptimizer(
            db, screens, constraint_map, merged_constraints
        )
        
        # 6. GROUP FORECASTS BY DATE
        forecasts_by_date = defaultdict(list)
        for f in slot_level_forecasts:
            forecasts_by_date[f["date"]].append(f)
        
        print(f"\n📅 Scheduling across {len(forecasts_by_date)} dates:")
        for date in sorted(forecasts_by_date.keys()):
            print(f"   - {date}: {len(forecasts_by_date[date])} forecasts")
        
        # 7. SCHEDULE SHOWS
        scheduling_results = []
        scheduled_show_ids = []
        
        print(f"\n🔄 Starting scheduling process...")
        
        for date_str in sorted(forecasts_by_date.keys()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            date_forecasts = forecasts_by_date[date_str]
            
            print(f"\n{'='*60}")
            print(f"Processing {date_str}")
            print(f"{'='*60}")
            
            # PHASE 1: PRIME SLOTS (demand-sorted)
            prime_forecasts = [f for f in date_forecasts if f.get("is_prime_slot", False)]
            prime_forecasts.sort(key=lambda x: x.get("slot_expected_demand", 0), reverse=True)
            
            print(f"\n🌟 PRIME SLOTS - {len(prime_forecasts)} forecasts")
            
            for i, forecast in enumerate(prime_forecasts, 1):
                movie_name = forecast["movie"]
                slot = forecast["slot"]
                demand = forecast.get("slot_expected_demand", 0)
                
                print(f"\n   [{i}/{len(prime_forecasts)}] {movie_name} @ {slot} - Demand: {demand:.0f}")
                
                screen = optimizer.find_best_screen(forecast, date_obj, allowed_movie_set)
                
                if not screen:
                    print(f"      ❌ No suitable screen found")
                    continue
                
                show = optimizer.schedule_show(forecast, screen, movies_by_id, "prime_allocation")
                
                if show:
                    capacity = optimizer.screen_capacity[screen.screen_id]
                    fill_ratio = demand / capacity if capacity > 0 else 0
                    
                    print(f"      ✅ Scheduled on {screen.screen_name}")
                    print(f"         Capacity: {capacity}, Fill: {fill_ratio:.1%}")
                    
                    scheduling_results.append({
                        "show_id": show.show_id,
                        "screen": screen.screen_name,
                        "screen_id": screen.screen_id,
                        "movie": movie_name,
                        "movie_id": forecast["movie_id"],
                        "date": date_str,
                        "slot": slot,
                        "forecast_demand": round(demand, 2),
                        "capacity": capacity,
                        "forecast_occupancy": round(fill_ratio, 2),
                        "is_prime_slot": True,
                        "phase": "prime_allocation"
                    })
                    scheduled_show_ids.append(show.show_id)
            
            # PHASE 2: REGULAR SLOTS (demand-sorted, unscheduled movies first)
            regular_forecasts = [f for f in date_forecasts if not f.get("is_prime_slot", False)]
            
            # Separate into unscheduled and scheduled movies
            unscheduled = []
            scheduled = []
            
            for f in regular_forecasts:
                movie_id = f["movie_id"]
                if optimizer.daily_movie_count[date_str][movie_id] == 0:
                    unscheduled.append(f)
                else:
                    scheduled.append(f)
            
            # Sort each group by demand
            unscheduled.sort(key=lambda x: x.get("slot_expected_demand", 0), reverse=True)
            scheduled.sort(key=lambda x: x.get("slot_expected_demand", 0), reverse=True)
            
            ordered_regular = unscheduled + scheduled
            
            print(f"\n📺 REGULAR SLOTS - {len(ordered_regular)} forecasts")
            print(f"   - Unscheduled movies first: {len(unscheduled)}")
            print(f"   - Already scheduled: {len(scheduled)}")
            
            for i, forecast in enumerate(ordered_regular, 1):
                movie_name = forecast["movie"]
                slot = forecast["slot"]
                demand = forecast.get("slot_expected_demand", 0)
                
                print(f"\n   [{i}/{len(ordered_regular)}] {movie_name} @ {slot} - Demand: {demand:.0f}")
                
                screen = optimizer.find_best_screen(forecast, date_obj, allowed_movie_set)
                
                if not screen:
                    print(f"      ❌ No suitable screen found")
                    continue
                
                show = optimizer.schedule_show(forecast, screen, movies_by_id, "regular_allocation")
                
                if show:
                    capacity = optimizer.screen_capacity[screen.screen_id]
                    fill_ratio = demand / capacity if capacity > 0 else 0
                    
                    print(f"      ✅ Scheduled on {screen.screen_name}")
                    print(f"         Capacity: {capacity}, Fill: {fill_ratio:.1%}")
                    
                    scheduling_results.append({
                        "show_id": show.show_id,
                        "screen": screen.screen_name,
                        "screen_id": screen.screen_id,
                        "movie": movie_name,
                        "movie_id": forecast["movie_id"],
                        "date": date_str,
                        "slot": slot,
                        "forecast_demand": round(demand, 2),
                        "capacity": capacity,
                        "forecast_occupancy": round(fill_ratio, 2),
                        "is_prime_slot": False,
                        "phase": "regular_allocation"
                    })
                    scheduled_show_ids.append(show.show_id)
        
        # 8. COMMIT TRANSACTION
        db.commit()
        print(f"\n✅ Transaction committed - {len(scheduled_show_ids)} shows created")
        
        # 9. PRINT DEBUG SUMMARY
        optimizer.debugger.print_summary()
        
        # 10. STORE RESULTS
        state.setdefault("result", {})
        state["result"]["scheduling"] = scheduling_results
        state["result"]["scheduled_show_ids"] = scheduled_show_ids
        
        # Calculate diagnostics
        movies_scheduled = set(r["movie"] for r in scheduling_results)
        prime_count = sum(1 for r in scheduling_results if r.get("is_prime_slot"))
        
        movie_show_counts = defaultdict(int)
        for r in scheduling_results:
            movie_show_counts[r["movie"]] += 1
        
        state["scheduling_diagnostics"] = {
            "total_shows": len(scheduled_show_ids),
            "prime_shows": prime_count,
            "regular_shows": len(scheduled_show_ids) - prime_count,
            "movies_scheduled": sorted(list(movies_scheduled)),
            "per_movie_counts": dict(movie_show_counts),
            "skipped_count": len(optimizer.debugger.skipped_forecasts),
            "capacity_issues": len(optimizer.debugger.capacity_issues)
        }
        
        state["output"] = (
            f"Scheduled {len(scheduled_show_ids)} shows "
            f"({prime_count} prime, {len(scheduled_show_ids) - prime_count} regular) "
            f"for {len(movies_scheduled)} movies"
        )
        
        print(f"\n{'='*80}")
        print(f"SCHEDULING NODE COMPLETE")
        print(f"{'='*80}\n")
    
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        state["output"] = f"Scheduling failed: {str(e)}"
        raise
    
    finally:
        db.close()
    
    return state