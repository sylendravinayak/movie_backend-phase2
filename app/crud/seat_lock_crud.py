from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from model.seat import SeatLock
from schemas.seat_schema import SeatLockCreate, SeatLockUpdate
from schemas import SeatLockStatus as SeatLockStatusEnum

class SeatLockCRUD:
    def create(self, db: Session, obj_in: SeatLockCreate):
        # Only consider ACTIVE locks (expires_at > now)
        now = datetime.utcnow()
        existing_lock = db.query(SeatLock).filter(
            SeatLock.seat_id == obj_in.seat_id,
            SeatLock.show_id == obj_in.show_id,
            SeatLock.status == SeatLockStatusEnum.LOCKED,
            SeatLock.expires_at > now
        ).first()
        if existing_lock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seat already locked for this show."
            )

        db_obj = SeatLock(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_all(self, db: Session, skip=0, limit=10):
        return db.query(SeatLock).offset(skip).limit(limit).all()

    def get_by_id(self, db: Session, lock_id: int):
        seat_lock = db.query(SeatLock).filter(SeatLock.lock_id == lock_id).first()
        if not seat_lock:
            raise HTTPException(status_code=404, detail="Seat lock not found")
        return seat_lock

    def update(self, db: Session, lock_id: int, obj_in: SeatLockUpdate):
        db_obj = self.get_by_id(db, lock_id)
        for key, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, lock_id: int):
        db_obj = self.get_by_id(db, lock_id)
        db.delete(db_obj)
        db.commit()
        return {"detail": "Seat lock removed successfully"}

    def release_expired_locks(self, db: Session):
        now = datetime.utcnow()
        # Delete rows instead of setting a non-existent EXPIRED enum
        expired_locks = db.query(SeatLock).filter(
            SeatLock.expires_at < now,
            SeatLock.status == SeatLockStatusEnum.LOCKED
        ).all()

        for lock in expired_locks:
            db.delete(lock)

        if expired_locks:
            db.commit()
        return len(expired_locks)