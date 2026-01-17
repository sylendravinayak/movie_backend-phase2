from sqlalchemy.orm import Session
from model import Booking, Show
from datetime import datetime, timedelta

def get_recent_booking_count(movie_id: int, days: int, db: Session):

    since = datetime.utcnow() - timedelta(days=days)

    return db.query(Booking).join(
        Show, Booking.show_id == Show.show_id
    ).filter(
        Show.movie_id == movie_id,
        Booking.booking_date >= since
    ).count()

def get_daily_booking_series(movie_id: int, days: int, db: Session):

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(Booking.booking_date)
        .select_from(Booking)
        .join(Show, Booking.show_id == Show.show_id)
        .filter(
            Show.movie_id == movie_id,
            Booking.booking_date >= since
        )
        .all()
    )

    return [r[0].date() for r in rows]

