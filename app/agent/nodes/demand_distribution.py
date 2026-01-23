"""
Dynamic Demand Distribution
- Learned slot patterns from historical data
- Day-of-week specific distributions
- Dynamic slot weights based on actual performance
"""
from langgraph.errors import NodeInterrupt
from agent.state import OpsState
from database import SessionLocal
from model.theatre import Screen
from model.seat import Seat
from model import Show
from sqlalchemy import text, func
from datetime import datetime, timedelta
import numpy as np

class SlotDistributor:
    """Intelligent slot-level demand distribution"""
    
    def __init__(self, db):
        self.db = db
        self.learned_weights = self._learn_slot_patterns()
        
    def _learn_slot_patterns(self):
        """Learn actual slot performance from historical data"""
        
        # Query historical slot performance
        results = self.db.execute(text("""
            SELECT 
                TO_CHAR(s.show_time, 'HH24:MI') as slot,
                EXTRACT(DOW FROM s.show_date) as day_of_week,
                AVG(booked_count.cnt) as avg_bookings,
                COUNT(*) as show_count
            FROM shows s
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as cnt
                FROM booked_seats bs
                WHERE bs.show_id = s.show_id
            ) booked_count ON true
            WHERE s.show_date >= CURRENT_DATE - INTERVAL '90 days'
            AND s.status = 'COMPLETED'
            GROUP BY slot, day_of_week
            HAVING COUNT(*) >= 3
        """)).fetchall()
        
        if not results:
            # Fallback to default patterns
            return self._default_patterns()
        
        # Build learned patterns
        patterns = {}
        for row in results:
            slot = row.slot
            dow = int(row.day_of_week)  # 0=Sunday, 6=Saturday
            avg_bookings = float(row.avg_bookings or 0)
            
            if slot not in patterns:
                patterns[slot] = {}
            patterns[slot][dow] = avg_bookings
        
        # Normalize to weights
        for slot in patterns:
            total = sum(patterns[slot].values()) or 1
            for dow in patterns[slot]:
                patterns[slot][dow] = patterns[slot][dow] / total
        
        return patterns
    
    def _default_patterns(self):
        """Default slot distribution when no historical data"""
        
        # Weekday pattern (Mon-Thu): 0,1,2,3,4
        weekday_dist = {
            "09:00": 0.75,
            "11:20": 0.85,
            "13:40": 0.95,
            "16:00": 1.05,
            "18:20": 1.25,
            "20:40": 1.15
        }
        
        # Weekend pattern (Fri-Sun): 5,6,0
        weekend_dist = {
            "09:00": 0.90,
            "11:20": 1.05,
            "13:40": 1.10,
            "16:00": 1.15,
            "18:20": 1.35,
            "20:40": 1.25
        }
        
        patterns = {}
        for slot in weekday_dist:
            patterns[slot] = {}
            # Weekdays
            for dow in [1, 2, 3, 4]:
                patterns[slot][dow] = weekday_dist[slot]
            # Weekend
            for dow in [5, 6, 0]:
                patterns[slot][dow] = weekend_dist[slot]
        
        return patterns
    
    def get_slot_weight(self, slot: str, target_date: str) -> float:
        """Get dynamic weight for a slot on a specific date"""
        
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        dow = dt.weekday()  # 0=Monday
        
        # Convert to 0=Sunday format
        dow_sunday = (dow + 1) % 7
        
        if slot in self.learned_weights and dow_sunday in self.learned_weights[slot]:
            return self.learned_weights[slot][dow_sunday]
        
        # Fallback
        default_weights = {
            "09:00": 0.80,
            "11:20": 0.90,
            "13:40": 1.00,
            "16:00": 1.10,
            "18:20": 1.30,
            "20:40": 1.20
        }
        return default_weights.get(slot, 1.0)
    
    def distribute_confidence(self, base_confidence: float, slot: str, 
                             demand: float, capacity: float) -> float:
        """Calculate slot-specific confidence"""
        
        # Adjust based on demand/capacity ratio
        fill_ratio = demand / max(capacity, 1)
        
        if fill_ratio < 0.2:
            # Low demand = higher uncertainty
            adj = -0.1
        elif fill_ratio > 0.8:
            # High demand = higher confidence
            adj = 0.05
        else:
            adj = 0
        
        # Prime time slots = slight confidence boost
        if slot in ["18:20", "20:40"]:
            adj += 0.03
        
        confidence = base_confidence + adj
        return round(max(0.4, min(confidence, 0.95)), 2)


def demand_distribution_node(state: OpsState):
    """Distribute movie-day demand to slot-level with dynamic weights"""
    
    db = SessionLocal()
    forecasts = state.get("result", {}).get("forecast", [])
    
    if not forecasts:
        raise NodeInterrupt("No forecast available for distribution")
    
    screens = db.query(Screen).filter(Screen.is_available == True).all()
    
    # Initialize distributor
    distributor = SlotDistributor(db)
    
    # Get dynamic time slots based on movie durations
    from agent.tools.slot_calculator import get_dynamic_time_slots
    from model import Movie
    
    movies = db.query(Movie).all()
    TIME_SLOTS = get_dynamic_time_slots(movies)
    
    if not TIME_SLOTS:
        # Fallback to standard slots
        TIME_SLOTS = ["09:00", "11:20", "13:40", "16:00", "18:20", "20:40"]
    
    # Normalize capacity constraints
    total_capacity = sum(
        db.query(Seat).filter(Seat.screen_id == s.screen_id).count()
        for s in screens
    )
    
    slots_per_day = len(TIME_SLOTS)
    distributed = []
    
    for f in forecasts:
        movie_day_demand = f.get("movie_day_demand", 0)
        base_confidence = f.get("confidence", 0.7)
        
        if not movie_day_demand:
            continue
        
        # Get dynamic weights for this date
        date_weights = {}
        for slot in TIME_SLOTS:
            date_weights[slot] = distributor.get_slot_weight(slot, f["date"])
        
        total_weight = sum(date_weights.values())
        
        # Distribute demand
        for slot in TIME_SLOTS:
            slot_weight = date_weights[slot]
            slot_demand = movie_day_demand * (slot_weight / total_weight)
            
            # Cap at physical capacity per slot
            max_slot_capacity = total_capacity
            slot_demand = min(slot_demand, max_slot_capacity)
            
            # Calculate slot-specific confidence
            slot_confidence = distributor.distribute_confidence(
                base_confidence, slot, slot_demand, max_slot_capacity
            )
            
            distributed.append({
                "movie_id": f["movie_id"],
                "movie": f["movie"],
                "date": f["date"],
                "slot": slot,
                "slot_expected_demand": round(slot_demand, 2),
                "movie_day_demand": movie_day_demand,
                "confidence": slot_confidence,
                "slot_weight": round(slot_weight, 2),
                "velocity": f.get("velocity", 1.0),
                "trend": f.get("trend", 1.0),
                "competition": f.get("competition", 0.5),
                "forecast_method": f.get("forecast_method", "unknown")
            })
    
    db.close()
    
    state["result"]["forecast"] = distributed
    state["forecast_scope"] = "slot_level"
    state["output"] = (
        f"Distributed {len(forecasts)} movie-days → {len(distributed)} slot-level forecasts "
        f"using learned patterns."
    )
    
    return state