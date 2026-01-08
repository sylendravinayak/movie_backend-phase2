from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from crud.seat_category_crud import seat_category_crud
from schemas.theatre_schema import (
    SeatCategoryCreate,
    SeatCategoryUpdate,
    SeatCategoryOut,
)
from typing import Optional
from schemas import UserRole
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
router = APIRouter(prefix="/seat-categories", tags=["Seat Categories"])


@router.post("/", response_model=SeatCategoryOut)
def create_category(category: SeatCategoryCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return seat_category_crud.create(db, category)


@router.get("/", response_model=list[SeatCategoryOut])
def get_all_categories(
    screen_id: Optional[int] = None,
    category_name: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    db: Session = Depends(get_db)
):
    filters = {"screen_id": screen_id, "category_name": category_name}
    return seat_category_crud.get_all(db, skip=skip, limit=limit, filters=filters)


@router.get("/{category_id}", response_model=SeatCategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db),current_user:dict=Depends(getcurrent_user(UserRole.ADMIN.value))):
    category = seat_category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=SeatCategoryOut)
def update_category(
    category_id: int, category_update: SeatCategoryUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    category = seat_category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return seat_category_crud.update(db, category, category_update)


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return seat_category_crud.remove(db, category_id)
