from sqlalchemy.orm import Session
from model import Booking, Show
from datetime import datetime, timedelta

def get_movie_demand(movie_id: int, db: Session):

    last_week = datetime.utcnow() - timedelta(days=7)

    return db.query(Booking).join(
        Show, Booking.show_id == Show.show_id
    ).filter(
        Show.movie_id == movie_id,
        Booking.booking_date >= last_week
    ).count()
