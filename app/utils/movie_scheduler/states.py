from typing import TypedDict, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session

class SchedulerState(TypedDict, total=False):
    db: Session
    Movie: Any
    movie_ids: List[int]
    start_date: date

    movies: List[Any]
    movies_with_signals: List[Dict]
    schedule_plan: List[Dict]

    status: str
