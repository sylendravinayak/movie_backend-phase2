from langgraph.errors import NodeInterrupt
from agent.state import OpsState
from database import SessionLocal
from model.theatre import Screen
from model.seat import Seat
from model import Show
from sqlalchemy import text, func
from datetime import datetime, timedelta
import numpy as np

FIXED_TIME_SLOTS = [
    "09:00",
    "12:00",
    "15:00",
    "18:00",
    "21:00"
]

SLOT_DURATION_MIN = 180
PRIME_SLOTS = {"18:00", "21:00"}

class SlotDistributor:
    """Intelligent slot-level demand distribution"""
    
    def __init__(self, db):
        self.db = db
        self.learned_weights = self._learn_slot_patterns()
    
        
    def _learn_slot_patterns(self):
        """Learn actual slot performance from historical data"""
        
        results = self.db.execute(text("""
            SELECT 
                TO_CHAR(s.show_time, 'HH24:MI') as slot_time,
                EXTRACT(DOW FROM s.show_date) as day_of_week,
                AVG(booked_count.cnt) as avg_bookings,
                COUNT(*) as show_count,
                STDDEV(booked_count.cnt) as booking_variance
            FROM shows s
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as cnt
                FROM booked_seats bs
                WHERE bs.show_id = s.show_id
            ) booked_count ON true
            WHERE s.show_date >= CURRENT_DATE - INTERVAL '90 days'
            AND s.status = 'COMPLETED'
            GROUP BY slot_time, day_of_week
            HAVING COUNT(*) >= 3
        """)).fetchall()
        
        if not results:
            return self._default_patterns()
        
        patterns_by_day = {}
        metadata = {}
        
        for row in results:
            slot_time = row.slot_time
            normalized_slot = self._normalize_slot(slot_time)
            dow = int(row.day_of_week)
            avg_bookings = float(row.avg_bookings or 0)
            show_count = int(row.show_count)
            variance = float(row.booking_variance or 0)
            
            if dow not in patterns_by_day:
                patterns_by_day[dow] = {}
            
            if normalized_slot not in patterns_by_day[dow]:
                patterns_by_day[dow][normalized_slot] = 0
            patterns_by_day[dow][normalized_slot] += avg_bookings
            
            metadata[(normalized_slot, dow)] = {
                'show_count': show_count,
                'variance': variance,
                'avg_bookings': avg_bookings
            }
        
        # Normalize PER DAY to preserve magnitude
        patterns = {}
        for dow, slots in patterns_by_day.items():
            total = sum(slots.values()) or 1
            for slot, value in slots.items():
                if slot not in patterns:
                    patterns[slot] = {}
                patterns[slot][dow] = value / total
        
        self.pattern_metadata = metadata
        return patterns
    
    def _default_patterns(self):
        """Default slot distribution with PRIME SLOTS HEAVILY emphasized"""
        
        # Weekday pattern (Mon-Thu): 1,2,3,4
        weekday_weights = {
            "09:00": 0.50,  # Morning - low
            "12:00": 0.65,  # Late morning - low
            "15:00": 0.75,  # Afternoon - moderate
            "18:00": 0.90,  # Evening start - good
            "21:00": 1.80,  # PRIME - DOMINANT
            "21:00": 1.60   # PRIME - STRONG
        }
        
        # Weekend pattern (Fri-Sun): 5,6,0
        weekend_weights = {
            "09:00": 0.70,  # Weekend morning - better
            "12:00": 0.95,  # Late morning - good
            "15:00": 1.10,  # Afternoon - strong
            "18:00": 1.30,  # Evening start - very good
            "21:00": 2.20,  # PRIME - PEAK WEEKEND
            "21:00": 2.00   # PRIME - PEAK WEEKEND
        }
        
        patterns = {}
        for slot in weekday_weights:
            patterns[slot] = {}
            for dow in [1, 2, 3, 4]:
                patterns[slot][dow] = weekday_weights[slot]
            for dow in [5, 6, 0]:
                patterns[slot][dow] = weekend_weights[slot]
        
        self.pattern_metadata = {}
        return patterns
    
    def is_prime_slot(self, slot: str) -> bool:
        """Check if slot is a prime slot - NO AMBIGUITY"""
        normalized = self._normalize_slot(slot)
        return normalized in PRIME_SLOTS
    
    def _normalize_slot(self, slot: str) -> str:
        h, m = map(int, slot.split(":"))
        minutes = h * 60 + m

        buckets = {
            "09:00": 9*60,
            "12:00": 12*60,
            "15:00": 15*60,
            "18:00": 18*60,
            "21:00": 21*60,
        }

        return min(buckets, key=lambda k: abs(buckets[k] - minutes))
    def get_slot_weight(self, slot: str, target_date: str) -> tuple:
        """
        Get dynamic weight for a slot on a specific date
        Returns: (weight, confidence, data_quality, is_prime)
        """
        
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        dow = dt.weekday()
        dow_sunday = (dow + 1) % 7
        
        normalized_slot = self._normalize_slot(slot)
        is_prime = normalized_slot in PRIME_SLOTS  # DIRECT CHECK
        
        if normalized_slot in self.learned_weights and dow_sunday in self.learned_weights[normalized_slot]:
            weight = self.learned_weights[normalized_slot][dow_sunday]
            
            metadata = self.pattern_metadata.get((normalized_slot, dow_sunday), {})
            show_count = metadata.get('show_count', 0)
            variance = metadata.get('variance', 0)
            avg_bookings = metadata.get('avg_bookings', 0)
            
            if show_count >= 10 and avg_bookings > 0:
                confidence = 0.9
                data_quality = 'learned'
            else:
                confidence = 0.5
                data_quality = 'learned_low_volume'
            
            return (weight, confidence, data_quality, is_prime)
        
        default_weights = {
            "09:00": 0.50,
            "12:00": 0.65,
            "15:00": 0.75,
            "18:00": 0.90,
            "21:00": 1.80,  # Prime
            "21:00": 1.60   # Prime
        }
        
        if dow_sunday in [5, 6, 0]:
            weight = default_weights.get(normalized_slot, 1.0) * 1.25
        else:
            weight = default_weights.get(normalized_slot, 1.0)
        
        return (weight, 0.4, 'fallback', is_prime)
    
    def enforce_prime_bias(self, slot_data: dict):
    
        PRIME_MULTIPLIER = 1.75  # real dominance, not cosmetic

        for slot, data in slot_data.items():
            if data["is_prime"]:
                data["weight"] *= PRIME_MULTIPLIER

        return slot_data
    def distribute_confidence(self, base_confidence: float, slot: str, 
                             demand: float, capacity: float, data_quality: str) -> float:
        """Calculate slot-specific confidence with capacity awareness"""
        
        confidence = base_confidence
        
        # Data quality adjustment
        if data_quality == 'learned':
            confidence += 0.1
        elif data_quality == 'fallback':
            confidence -= 0.15
        
        # Capacity-aware confidence
        if capacity > 0:
            fill_ratio = demand / capacity
            
            if fill_ratio < 0.2:
                confidence -= 0.1
            elif 0.5 <= fill_ratio <= 0.85:
                confidence += 0.05
            elif fill_ratio > 1.5:
                confidence -= 0.15
        
        # Prime slot boost
        if self.is_prime_slot(slot):
            confidence += 0.08  # Increased from 0.05
        
        return round(max(0.35, min(confidence, 0.95)), 2)


def demand_distribution_node(state: OpsState):
    """Distribute movie-day demand to slot-level with EXPLICIT prime detection"""
    
    db = SessionLocal()
    forecasts = state.get("result", {}).get("forecast", [])
    
    if not forecasts:
        raise NodeInterrupt("No forecast available for distribution")
    
    screens = db.query(Screen).filter(Screen.is_available == True).all()
    distributor = SlotDistributor(db)
    
    
    
    TIME_SLOTS = FIXED_TIME_SLOTS.copy()
    
    
    # Calculate REALISTIC capacity per slot
    total_capacity_per_slot = sum(
    db.query(Seat).filter(Seat.screen_id == s.screen_id).count()
    for s in screens
    ) 
    
    distributed = []
    
    for f in forecasts:
        movie_day_demand = f.get("movie_day_demand", 0)
        
        if not movie_day_demand:
            continue
        
        # Get dynamic weights for this date
        slot_data = {}
        for slot in TIME_SLOTS:
            weight, slot_confidence, data_quality, is_prime = distributor.get_slot_weight(slot, f["date"])
            slot_data[slot] = {
                'weight': weight,
                'confidence': slot_confidence,
                'data_quality': data_quality,
                'is_prime': is_prime  # EXPLICIT FLAG
            }
        
        slot_data = distributor.enforce_prime_bias(slot_data)
        total_weight = sum(data['weight'] for data in slot_data.values())
        
        # Distribute demand proportionally
        for slot in TIME_SLOTS:
            slot_info = slot_data[slot]
            slot_weight = slot_info['weight']
            slot_demand = movie_day_demand * (slot_weight / total_weight)
            
            
            distributed.append({
                "movie_id": f["movie_id"],
                "movie": f["movie"],
                "date": f["date"],
                "slot": slot,
                "slot_expected_demand": round(slot_demand, 2),
                "movie_day_demand": movie_day_demand,
                "slot_weight": round(slot_weight, 2),
                "demand_share": round(slot_weight / total_weight, 3),
                "data_quality": slot_info['data_quality'],
                "is_prime_slot": slot_info['is_prime'],  # EXPLICIT
                "velocity": f.get("velocity"),
                "trend": f.get("trend"),
                "competition": f.get("competition"),
                "forecast_method": f.get("forecast_method", "unknown")
            })
    
    db.close()
    
 
    state["result"]["forecast"] = distributed
    state["forecast_scope"] = "slot_level"
  
    return state