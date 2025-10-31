from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from database import get_db
from sqlalchemy.orm import Session
from crud.booked_seat_crud import booked_seat_crud

router = APIRouter(prefix="/booked_seats", tags=["Bookings"])
@router.get("/")
def get_booked_seats(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    booking_id: Optional[int] = Query(None),
    seat_id: Optional[int] = Query(None),
    show_id: Optional[int] = Query(None),
):
    filters = {}

    if booking_id is not None:
        filters["booking_id"] = booking_id
    if seat_id is not None:
        filters["seat_id"] = seat_id
    if show_id is not None:
        filters["show_id"] = show_id

    return booked_seat_crud.get_all(db, skip=skip, limit=limit, filters=filters)