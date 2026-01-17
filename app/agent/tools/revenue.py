from sqlalchemy.orm import Session
from model import BookedSeat
from sqlalchemy import func

def get_show_revenue(show_id: int, db: Session):
    """calculate total revenue for a given show"""
    revenue = db.query(func.sum(BookedSeat.price)).filter(
        BookedSeat.show_id == show_id
    ).scalar()

    return float(revenue or 0)
