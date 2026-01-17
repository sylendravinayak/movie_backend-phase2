from sqlalchemy.orm import Session
from model import Show, Seat, BookedSeat

def get_show_occupancy(show_id: int, db: Session):
    """calculate occupancy rate for a given show"""
    screen_id = db.query(Show.screen_id).filter(
        Show.show_id == show_id
    ).scalar()

    total_seats = db.query(Seat).filter(
        Seat.screen_id == screen_id
    ).count()

    booked_seats = db.query(BookedSeat).filter(
        BookedSeat.show_id == show_id
    ).count()

    if total_seats == 0:
        return 0.0

    return booked_seats / total_seats
