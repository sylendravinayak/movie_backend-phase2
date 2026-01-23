from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from model import Booking, Show
from datetime import datetime, timedelta

def get_recent_booking_count(movie_id: int, days: int, db: Session):
    """Get total booking count for a movie in the last N days"""
    since = datetime.utcnow() - timedelta(days=days)
    
    return db.query(Booking).join(
        Show, Booking.show_id == Show.show_id
    ).filter(
        Show.movie_id == movie_id,
        Booking.booking_date >= since
    ).count()

def get_daily_booking_series(movie_id: int, days: int, db: Session):
    """
    Get daily booking counts for a movie over the last N days
    Returns: List of tuples [(date, count), (date, count), ...]
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    rows = (
        db.query(
            cast(Booking.booking_date, Date).label('date'),
            func.count(Booking.booking_id).label('count')
        )
        .select_from(Booking)
        .join(Show, Booking.show_id == Show.show_id)
        .filter(
            Show.movie_id == movie_id,
            Booking.booking_date >= since
        )
        .group_by(cast(Booking.booking_date, Date))
        .order_by(cast(Booking.booking_date, Date))
        .all()
    )
    
    # Convert to list of (date, count) tuples
    return [(r.date, r.count) for r in rows]