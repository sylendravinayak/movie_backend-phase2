"""
Dynamic Slot Calculator
Generates time slots based on movie durations and buffer times
"""
from datetime import time, datetime, timedelta
from typing import List, Dict, Tuple
from model import Movie

# Theater operating hours
THEATER_OPEN_TIME = time(9, 0)   # 9:00 AM
THEATER_CLOSE_TIME = time(23, 30)  # 11:30 PM

# Buffer times
CLEANING_BUFFER_MIN = 15  # Cleaning between shows
PREVIEW_DURATION_MIN = 10  # Trailers/ads before movie


class SlotCalculator:
    """Calculate optimal time slots for movies"""
    
    def __init__(self, movies: List[Movie], buffer_min: int = CLEANING_BUFFER_MIN):
        self.movies = {m.movie_id: m for m in movies}
        self.buffer_min = buffer_min
        self.slot_cache = {}
    
    def get_movie_duration(self, movie_id: int) -> int:
        """Get total duration including previews"""
        movie = self.movies.get(movie_id)
        if not movie:
            return 120  # Default 2 hours
        
        base_duration = movie.duration or 120
        return base_duration + PREVIEW_DURATION_MIN
    
    def calculate_end_time(self, start_time: time, movie_id: int) -> time:
        """Calculate when movie ends"""
        duration = self.get_movie_duration(movie_id)
        
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        
        return end_dt.time()
    
    def get_next_available_slot(self, after_time: time, movie_id: int) -> time:
        """
        Calculate next available slot after given time
        Includes buffer for cleaning
        """
        duration = self.get_movie_duration(movie_id)
        
        start_dt = datetime.combine(datetime.today(), after_time)
        # Add movie duration + buffer
        next_dt = start_dt + timedelta(minutes=duration + self.buffer_min)
        
        next_time = next_dt.time()
        
        # Check if within operating hours
        if next_time > THEATER_CLOSE_TIME:
            return None  # Can't fit another show
        
        return next_time
    
    def generate_slots_for_day(self, movie_schedule: List[Tuple[int, int]]) -> List[Dict]:
        """
        Generate time slots for a day given movie assignments
        movie_schedule: [(movie_id, screen_id), ...]
        Returns: [{"screen_id": 1, "movie_id": 1, "start": "09:00", "end": "11:30"}, ...]
        """
        
        # Group by screen
        screen_schedule = {}
        for movie_id, screen_id in movie_schedule:
            screen_schedule.setdefault(screen_id, []).append(movie_id)
        
        all_slots = []
        
        for screen_id, movie_ids in screen_schedule.items():
            current_time = THEATER_OPEN_TIME
            
            for movie_id in movie_ids:
                duration = self.get_movie_duration(movie_id)
                
                # Calculate end time
                start_dt = datetime.combine(datetime.today(), current_time)
                end_dt = start_dt + timedelta(minutes=duration)
                end_time = end_dt.time()
                
                # Check if fits in operating hours
                if end_time > THEATER_CLOSE_TIME:
                    break  # Skip this show
                
                all_slots.append({
                    "screen_id": screen_id,
                    "movie_id": movie_id,
                    "start_time": current_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "duration_min": duration - PREVIEW_DURATION_MIN,  # Actual movie
                    "total_duration_min": duration
                })
                
                # Next slot starts after buffer
                next_start_dt = end_dt + timedelta(minutes=self.buffer_min)
                current_time = next_start_dt.time()
                
                if current_time >= THEATER_CLOSE_TIME:
                    break
        
        return all_slots
    
    def get_standard_slots(self, max_duration: int = 180) -> List[str]:
        """
        Generate standard time slots assuming a typical movie duration
        Used for forecasting before actual scheduling
        """
        slots = []
        current_time = THEATER_OPEN_TIME
        
        while True:
            slots.append(current_time.strftime("%H:%M"))
            
            # Next slot
            start_dt = datetime.combine(datetime.today(), current_time)
            next_dt = start_dt + timedelta(minutes=max_duration + self.buffer_min)
            current_time = next_dt.time()
            
            # Check if we can fit another full show
            end_check = datetime.combine(datetime.today(), current_time) + timedelta(minutes=max_duration)
            if end_check.time() > THEATER_CLOSE_TIME:
                break
        
        return slots
    
    def can_fit_show(self, start_time: time, movie_id: int) -> bool:
        """Check if a movie can fit starting at given time"""
        duration = self.get_movie_duration(movie_id)
        
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        
        return end_dt.time() <= THEATER_CLOSE_TIME
    
    def calculate_max_shows_per_day(self, movie_id: int) -> int:
        """Calculate theoretical maximum shows per day for this movie"""
        duration = self.get_movie_duration(movie_id)
        
        # Operating hours in minutes
        open_dt = datetime.combine(datetime.today(), THEATER_OPEN_TIME)
        close_dt = datetime.combine(datetime.today(), THEATER_CLOSE_TIME)
        operating_minutes = (close_dt - open_dt).seconds / 60
        
        # How many shows can fit
        slot_duration = duration + self.buffer_min
        max_shows = int(operating_minutes / slot_duration)
        
        return max_shows


def get_dynamic_time_slots(movies: List[Movie]) -> List[str]:
    """
    Get dynamic time slots based on movie durations
    Returns standard slots for forecasting phase
    """
    if not movies:
        # Default slots
        return ["09:00", "11:30", "14:00", "16:30", "19:00", "21:30"]
    
    # Find longest movie to use as slot spacing
    max_duration = max((m.duration or 120) for m in movies)
    
    calculator = SlotCalculator(movies)
    slots = calculator.get_standard_slots(max_duration=max_duration)
    
    return slots


def validate_schedule_timing(schedule: List[Dict], movies: Dict[int, Movie]) -> List[Dict]:
    """
    Validate and adjust schedule for timing conflicts
    Returns: List of errors/warnings
    """
    issues = []
    
    # Group by screen
    by_screen = {}
    for item in schedule:
        screen_id = item.get("screen_id")
        by_screen.setdefault(screen_id, []).append(item)
    
    # Check each screen for conflicts
    for screen_id, shows in by_screen.items():
        # Sort by time
        shows_sorted = sorted(shows, key=lambda x: x.get("start_time", "00:00"))
        
        for i in range(len(shows_sorted) - 1):
            current = shows_sorted[i]
            next_show = shows_sorted[i + 1]
            
            current_end = datetime.strptime(current.get("end_time", "00:00"), "%H:%M").time()
            next_start = datetime.strptime(next_show.get("start_time", "00:00"), "%H:%M").time()
            
            # Check for overlap
            if current_end > next_start:
                issues.append({
                    "type": "overlap",
                    "screen_id": screen_id,
                    "show_1": current.get("show_id"),
                    "show_2": next_show.get("show_id"),
                    "message": f"Shows overlap on screen {screen_id}"
                })
            
            # Check for insufficient buffer
            current_end_dt = datetime.combine(datetime.today(), current_end)
            next_start_dt = datetime.combine(datetime.today(), next_start)
            gap_minutes = (next_start_dt - current_end_dt).seconds / 60
            
            if gap_minutes < CLEANING_BUFFER_MIN:
                issues.append({
                    "type": "insufficient_buffer",
                    "screen_id": screen_id,
                    "gap_minutes": gap_minutes,
                    "message": f"Only {gap_minutes}min buffer between shows on screen {screen_id}"
                })
    
    return issues