from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.seat_schema import SeatCreate, SeatUpdate, SeatOut
from schemas import UserRole
from crud.seat_crud import seat_crud
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
router = APIRouter(prefix="/seats", tags=["Seats"])

@router.post("/", response_model=List[SeatOut])
def create_seat(seat: List[SeatCreate], db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Create a new seat"""
    return seat_crud.create(db=db, obj_in_list=seat)



@router.get("/", response_model=List[SeatOut])
def get_all_seats(db: Session = Depends(get_db), skip: int = 0, limit: int = 10,payload: dict = Depends(JWTBearer())):
    """Fetch all seats"""
    return seat_crud.get_all(db=db, skip=skip, limit=limit)

@router.get("/{seat_id}", response_model=SeatOut)
def get_seat(seat_id: int, db: Session = Depends(get_db), payload: dict = Depends(JWTBearer())):
    """Fetch a seat by ID"""
    db_seat = seat_crud.get(db=db, id=seat_id)
    if not db_seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    return db_seat

@router.put("/{seat_id}", response_model=SeatOut)
def update_seat(seat_id: int, seat: SeatUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Update seat details"""
    db_seat = seat_crud.get(db=db, id=seat_id)
    if not db_seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    return seat_crud.update(db=db, db_obj=db_seat, obj_in=seat)

@router.delete("/{seat_id}")
def delete_seat(seat_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Delete a seat"""
    db_seat = seat_crud.get(db=db, id=seat_id)
    if not db_seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    seat_crud.remove(db=db, id=seat_id)
    return {"message": "Seat deleted successfully"}
