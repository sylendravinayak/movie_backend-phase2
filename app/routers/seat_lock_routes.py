from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from schemas.seat_schema import SeatLockCreate, SeatLockUpdate
from crud.seat_lock_crud import SeatLockCRUD
from database import get_db

router = APIRouter(prefix="/seatlocks", tags=["Seat Locks"])
seatlock_crud = SeatLockCRUD()


@router.post("/")
def create_seat_lock(obj_in: SeatLockCreate, db: Session = Depends(get_db)):
    return seatlock_crud.create(db, obj_in)


@router.get("/")
def get_all_seat_locks(db: Session = Depends(get_db), skip: int = 0, limit: int = 10):
    return seatlock_crud.get_all(db, skip, limit)


@router.get("/{lock_id}")
def get_seat_lock(lock_id: int, db: Session = Depends(get_db)):
    return seatlock_crud.get_by_id(db, lock_id)


@router.put("/{lock_id}")
def update_seat_lock(lock_id: int, obj_in: SeatLockUpdate, db: Session = Depends(get_db)):
    return seatlock_crud.update(db, lock_id, obj_in)


@router.delete("/{lock_id}")
def delete_seat_lock(lock_id: int, db: Session = Depends(get_db)):
    return seatlock_crud.remove(db, lock_id)


# 🔁 background cleanup endpoint
@router.post("/cleanup")
def cleanup_expired_locks(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(seatlock_crud.release_expired_locks, db)
    return {"message": "Expired locks cleanup scheduled"}
