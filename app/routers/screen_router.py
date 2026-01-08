from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.theatre_schema import ScreenCreate, ScreenUpdate, ScreenOut
from crud.screen_crud import screen_crud
from schemas import UserRole
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
router = APIRouter(prefix="/screens", tags=["Screens"])

@router.post("/", response_model=ScreenOut)
def create_screen(screen: ScreenCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Create a new screen"""
    return screen_crud.create(db=db, obj_in=screen)

@router.get("/", response_model=List[ScreenOut])
def get_all_screens(db: Session = Depends(get_db), skip: int = 0, limit: int = 10,name: str = None,type: str = None,total_seats: int = None,is_available: bool = None):
    """Fetch all screens"""
    filters={
        "screen_name": name,
        "screen_type": type,
        "total_seats": total_seats,
        "is_available": is_available
    }
    return screen_crud.get_all(db=db, skip=skip, limit=limit, filters=filters)


@router.get("/{screen_id}", response_model=ScreenOut)
def get_screen(screen_id: int, db: Session = Depends(get_db)):
    """Fetch a screen by ID"""
    db_screen = screen_crud.get(db=db, id=screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return db_screen

@router.put("/{screen_id}", response_model=ScreenOut)
def update_screen(screen_id: int, screen: ScreenUpdate, db: Session = Depends(get_db),current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Update screen details"""
    db_screen = screen_crud.get(db=db, id=screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen_crud.update(db=db, db_obj=db_screen, obj_in=screen)

@router.delete("/{screen_id}")
def delete_screen(screen_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    """Delete a screen"""
    db_screen = screen_crud.get(db=db, id=screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    screen_crud.remove(db=db, id=screen_id)
    return {"message": "Screen deleted successfully"}
