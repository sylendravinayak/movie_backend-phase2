"""
Dynamic Configuration Management
All "magic numbers" configurable here
"""
from typing import Dict, List
from datetime import time

class TheatreConfig:
    """Main configuration for theatre operations"""
    
    # ==================== FORECASTING ====================
    FORECAST_HORIZON_DAYS = 7
    MIN_HISTORY_FOR_ML = 7  # Minimum days of data for Prophet
    HISTORY_LOOKBACK_DAYS = 60  # How far back to look for training
    
    # Forecast confidence thresholds
    MIN_CONFIDENCE = 0.40
    MAX_CONFIDENCE = 0.95
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    
    # Capacity utilization
    MAX_CAPACITY_UTILIZATION = 1.2  # 120% overbooking allowed
    
    # ==================== SCHEDULING ====================
    # Standard show slots (can be customized per theater)
    TIME_SLOTS = ["09:00", "11:20", "13:40", "16:00", "18:20", "20:40"]
    
    # Prime time definition
    PRIME_TIME_SLOTS = {"18:20", "20:40"}
    PRIME_TIME_START = time(18, 0)
    PRIME_TIME_END = time(23, 0)
    
    # Show duration
    DEFAULT_SHOW_DURATION_MIN = 120
    BUFFER_BETWEEN_SHOWS_MIN = 20  # Cleaning time
    
    # Constraint defaults
    DEFAULT_MIN_SHOWS_PER_DAY = 2
    DEFAULT_MAX_SHOWS_PER_DAY = 6
    DEFAULT_PRIME_QUOTA = 2
    
    # ==================== PRICING ====================
    # Price boundaries
    MIN_PRICE_RATIO = 0.65  # 65% of base price
    MAX_PRICE_RATIO = 1.60  # 160% of base price
    
    # Surge pricing thresholds
    HIGH_DEMAND_THRESHOLD = 0.75  # 75% occupancy
    LOW_DEMAND_THRESHOLD = 0.30   # 30% occupancy
    
    # Surge multipliers
    MAX_SURGE_MULTIPLIER = 1.50  # 50% price increase max
    MAX_DISCOUNT_MULTIPLIER = 0.70  # 30% discount max
    
    # Time-based pricing
    LAST_MINUTE_HOURS = 6
    LAST_MINUTE_PREMIUM = 1.15
    
    DAY_BEFORE_HOURS = 24
    DAY_BEFORE_PREMIUM = 1.08
    
    # Day of week multipliers
    WEEKEND_DAYS = [4, 5, 6]  # Friday, Saturday, Sunday
    WEEKEND_MULTIPLIER = 1.08
    WEEKDAY_MULTIPLIER = 0.98
    
    # Slot multipliers
    SLOT_MULTIPLIERS = {
        "morning": 0.92,    # Before 12pm
        "afternoon": 1.04,  # 12pm-6pm
        "prime": 1.12       # 6pm-11pm
    }
    
    # Price rounding
    PRICE_ROUND_TO = 5  # Round to nearest 5
    
    # ==================== RESCHEDULING ====================
    MIN_CONFIDENCE_FOR_RESCHEDULE = 0.55
    MIN_BOOKING_RATIO = 0.15  # 15% booked to keep show
    
    UNDERPERFORM_GAP = -0.35  # 35% below forecast
    OVERPERFORM_GAP = 0.30    # 30% above forecast
    
    CANCELLATION_GAP = -0.45  # 45% below forecast
    HOURS_BEFORE_CANCEL = 6   # Don't cancel within 6 hours
    
    # ==================== SLOT DISTRIBUTION ====================
    # Default slot weights (if no historical data)
    DEFAULT_WEEKDAY_WEIGHTS = {
        "09:00": 0.75,
        "11:20": 0.85,
        "13:40": 0.95,
        "16:00": 1.05,
        "18:20": 1.25,
        "20:40": 1.15
    }
    
    DEFAULT_WEEKEND_WEIGHTS = {
        "09:00": 0.90,
        "11:20": 1.05,
        "13:40": 1.10,
        "16:00": 1.15,
        "18:20": 1.35,
        "20:40": 1.25
    }
    
    # ==================== ML MODELS ====================
    # Prophet configuration
    PROPHET_CHANGEPOINT_PRIOR = 0.05
    PROPHET_SEASONALITY_PRIOR = 10.0
    PROPHET_INTERVAL_WIDTH = 0.80
    
    # ==================== EXTERNAL SIGNALS ====================
    # Google Trends weight
    TREND_SIGNAL_WEIGHT = 1.0
    
    # Competition impact
    MAX_COMPETITION_PENALTY = 0.3  # Max 30% reduction
    
    # ==================== PERFORMANCE ====================
    # Database query limits
    MAX_HISTORY_DAYS = 90
    MIN_SHOWS_FOR_PATTERN_LEARNING = 3
    
    # Batch processing
    BATCH_SIZE = 100
    
    @classmethod
    def get_slot_time_category(cls, hour: int) -> str:
        """Categorize time slot for pricing"""
        if hour < 12:
            return "morning"
        elif hour < 18:
            return "afternoon"
        else:
            return "prime"
    
    @classmethod
    def is_weekend(cls, day_of_week: int) -> bool:
        """Check if day is weekend (0=Monday, 6=Sunday)"""
        return day_of_week in cls.WEEKEND_DAYS
    
    @classmethod
    def is_prime_time(cls, show_time: time) -> bool:
        """Check if time is in prime time"""
        return cls.PRIME_TIME_START <= show_time < cls.PRIME_TIME_END


class MovieConstraints:
    """Movie-specific constraints"""
    
    def __init__(self, movie_name: str, constraints: Dict = None):
        self.movie_name = movie_name
        self.constraints = constraints or {}
    
    @property
    def min_shows_per_day(self) -> int:
        return self.constraints.get(
            "min_shows_per_day", 
            TheatreConfig.DEFAULT_MIN_SHOWS_PER_DAY
        )
    
    @property
    def max_shows_per_day(self) -> int:
        return self.constraints.get(
            "max_shows_per_day",
            TheatreConfig.DEFAULT_MAX_SHOWS_PER_DAY
        )
    
    @property
    def prime_show_quota(self) -> int:
        return self.constraints.get(
            "prime_show_quota",
            TheatreConfig.DEFAULT_PRIME_QUOTA
        )
    
    @property
    def min_screen_capacity(self) -> int:
        """Minimum screen capacity for this movie"""
        return self.constraints.get("min_screen_capacity", 0)
    
    @property
    def preferred_format(self) -> str:
        """Preferred format (2D, 3D, IMAX, etc.)"""
        return self.constraints.get("preferred_format", "2D")


# Example usage
def load_movie_constraints(constraint_list: List[Dict]) -> Dict[str, MovieConstraints]:
    """Convert constraint list to MovieConstraints objects"""
    return {
        c["movie"]: MovieConstraints(c["movie"], c)
        for c in constraint_list
    }


# Environment-specific overrides
class ProductionConfig(TheatreConfig):
    """Production environment settings"""
    MIN_CONFIDENCE = 0.50  # Higher bar for production
    MAX_SURGE_MULTIPLIER = 1.40  # More conservative pricing


class DevelopmentConfig(TheatreConfig):
    """Development environment settings"""
    FORECAST_HORIZON_DAYS = 3  # Shorter for testing
    MIN_HISTORY_FOR_ML = 3