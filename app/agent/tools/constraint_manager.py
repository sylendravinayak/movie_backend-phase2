"""
Constraint Manager - Merges and validates MongoDB and user constraints
"""
from typing import Dict, List, Optional, Tuple
from database import get_mongo_db
from langgraph.errors import NodeInterrupt
from pydantic import BaseModel
from datetime import date, datetime

class MergedConstraints(BaseModel):
    """Unified constraints for a movie"""
    movie_id: str
    movie_name: str
    
    # Show constraints
    min_shows_per_day: int
    max_shows_per_day: int
    show_reduction_allowed: bool
    
    # Screen constraints
    allowed_screens: List[str]
    screen_change_allowed: bool
    screen_change_requires_approval: bool
    
    # Slot constraints
    prime_time_required: bool
    prime_show_quota: Optional[int] = None
    
    # Screening window
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Source tracking
    constraints_source: str  # "mongodb", "user", "merged"


class ConstraintManager:
    """Manages and validates screening constraints"""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.mongo_db = get_mongo_db()
        self.constraints_collection = self.mongo_db["screen_constraints"]
    
    def _get_mongodb_constraints(self, movie_id: str) -> Optional[Dict]:
        """Fetch constraints from MongoDB"""
        doc = self.constraints_collection.find_one({"movie_id": movie_id})
        return doc.get("screening_constraints") if doc else None
    
    def _parse_mongodb_constraints(self, movie_id: str, movie_name: str, 
                                   mongo_constraints: Dict) -> MergedConstraints:
        """Convert MongoDB constraints to MergedConstraints"""
        
        show_constraints = mongo_constraints.get("show_constraints", {})
        screen_constraints = mongo_constraints.get("screen_constraints", {})
        slot_constraints = mongo_constraints.get("slot_constraints", {})
        screening_window = mongo_constraints.get("screening_window", {})
        
        # Parse dates
        start_date = None
        end_date = None
        if screening_window.get("start_date"):
            start_date = datetime.strptime(screening_window["start_date"], "%Y-%m-%d").date()
        if screening_window.get("end_date"):
            end_date = datetime.strptime(screening_window["end_date"], "%Y-%m-%d").date()
        
        return MergedConstraints(
            movie_id=movie_id,
            movie_name=movie_name,
            min_shows_per_day=show_constraints.get("min_shows_per_day", 0),
            max_shows_per_day=show_constraints.get("max_shows_per_day", 999),
            show_reduction_allowed=show_constraints.get("show_reduction_allowed", True),
            allowed_screens=screen_constraints.get("allowed_screens", []),
            screen_change_allowed=screen_constraints.get("screen_change_allowed", True),
            screen_change_requires_approval=screen_constraints.get("screen_change_requires_approval", False),
            prime_time_required=slot_constraints.get("prime_time_required", False),
            prime_show_quota=slot_constraints.get("prime_show_quota"),
            start_date=start_date,
            end_date=end_date,
            constraints_source="mongodb"
        )
    
    def merge_constraints(self, movie_id: str, movie_name: str,
                         user_constraints: Optional[Dict] = None) -> Tuple[MergedConstraints, List[str]]:
        """
        Merge MongoDB and user constraints, validate conflicts
        Returns: (merged_constraints, conflict_messages)
        """
        
        # Get MongoDB constraints
        mongo_data = self._get_mongodb_constraints(movie_id)
        
        conflicts = []
        
        if not mongo_data and not user_constraints:
            # No constraints - use defaults
            return MergedConstraints(
                movie_id=movie_id,
                movie_name=movie_name,
                min_shows_per_day=0,
                max_shows_per_day=999,
                show_reduction_allowed=True,
                allowed_screens=[],
                screen_change_allowed=True,
                screen_change_requires_approval=False,
                prime_time_required=False,
                constraints_source="default"
            ), []
        
        # Start with MongoDB constraints as base
        if mongo_data:
            merged = self._parse_mongodb_constraints(movie_id, movie_name, mongo_data)
        else:
            merged = MergedConstraints(
                movie_id=movie_id,
                movie_name=movie_name,
                min_shows_per_day=0,
                max_shows_per_day=999,
                show_reduction_allowed=True,
                allowed_screens=[],
                screen_change_allowed=True,
                screen_change_requires_approval=False,
                prime_time_required=False,
                constraints_source="user"
            )
        
        # Apply user constraints and check for conflicts
        if user_constraints:
            user_min = user_constraints.get("min_shows_per_day")
            user_max = user_constraints.get("max_shows_per_day")
            user_prime_quota = user_constraints.get("prime_show_quota")
            
            # Validate min_shows_per_day
            if user_min is not None:
                if mongo_data:
                    mongo_min = merged.min_shows_per_day
                    if user_min < mongo_min:
                        conflicts.append(
                            f"❌ {movie_name}: User min_shows_per_day ({user_min}) "
                            f"is less than MongoDB minimum ({mongo_min})"
                        )
                    elif user_min > merged.max_shows_per_day:
                        conflicts.append(
                            f"❌ {movie_name}: User min_shows_per_day ({user_min}) "
                            f"exceeds max_shows_per_day ({merged.max_shows_per_day})"
                        )
                    else:
                        merged.min_shows_per_day = max(user_min, mongo_min)
                else:
                    merged.min_shows_per_day = user_min
            
            # Validate max_shows_per_day
            if user_max is not None:
                if mongo_data:
                    mongo_max = merged.max_shows_per_day
                    if user_max > mongo_max:
                        conflicts.append(
                            f"❌ {movie_name}: User max_shows_per_day ({user_max}) "
                            f"exceeds MongoDB maximum ({mongo_max})"
                        )
                    elif user_max < merged.min_shows_per_day:
                        conflicts.append(
                            f"❌ {movie_name}: User max_shows_per_day ({user_max}) "
                            f"is less than min_shows_per_day ({merged.min_shows_per_day})"
                        )
                    else:
                        merged.max_shows_per_day = min(user_max, mongo_max)
                else:
                    if user_max < merged.min_shows_per_day:
                        conflicts.append(
                            f"❌ {movie_name}: User max_shows_per_day ({user_max}) "
                            f"is less than min_shows_per_day ({merged.min_shows_per_day})"
                        )
                    else:
                        merged.max_shows_per_day = user_max
            
            # Validate prime_show_quota
            if user_prime_quota is not None:
                if user_prime_quota > merged.max_shows_per_day:
                    conflicts.append(
                        f"⚠️ {movie_name}: User prime_show_quota ({user_prime_quota}) "
                        f"exceeds max_shows_per_day ({merged.max_shows_per_day}). "
                        f"Capping at {merged.max_shows_per_day}."
                    )
                    merged.prime_show_quota = merged.max_shows_per_day
                else:
                    merged.prime_show_quota = user_prime_quota
            
            # Check if prime_time_required and no quota set
            if merged.prime_time_required and merged.prime_show_quota is None:
                # Set default: all shows must be prime
                merged.prime_show_quota = merged.max_shows_per_day
            
            merged.constraints_source = "merged" if mongo_data else "user"
        
        return merged, conflicts
    
    def validate_all_constraints(self, movie_constraints: List[Dict]) -> Tuple[Dict[str, MergedConstraints], List[str]]:
        """
        Validate constraints for all movies
        Returns: (movie_id -> MergedConstraints mapping, all_conflicts)
        """
        from model import Movie
        
        merged_map = {}
        all_conflicts = []
        
        for constraint in movie_constraints:
            movie_name = constraint.get("movie")
            
            # Get movie_id from database
            movie = self.db_session.query(Movie).filter(Movie.title == movie_name).first()
            if not movie:
                all_conflicts.append(f"❌ Movie '{movie_name}' not found in database")
                continue
            
            movie_id = str(movie.movie_id)
            
            merged, conflicts = self.merge_constraints(
                movie_id, 
                movie_name,
                {
                    "min_shows_per_day": constraint.get("min_shows_per_day"),
                    "max_shows_per_day": constraint.get("max_shows_per_day"),
                    "prime_show_quota": constraint.get("prime_show_quota")
                }
            )
            
            merged_map[movie_id] = merged
            all_conflicts.extend(conflicts)
        
        return merged_map, all_conflicts