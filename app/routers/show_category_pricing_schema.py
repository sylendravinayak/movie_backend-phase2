from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from crud.show_category_pricing_crud import show_category_pricing_crud
from schemas.theatre_schema import (
    ShowCategoryPricingCreate,
    ShowCategoryPricingUpdate,
    ShowCategoryPricingOut
)
from model import ShowCategoryPricing
from schemas import UserRole
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
router = APIRouter(prefix="/show-category-pricing", tags=["Show Category Pricing"])

# -----------------------------
# CREATE PRICING
# -----------------------------
@router.post("/", response_model=ShowCategoryPricingOut, status_code=status.HTTP_201_CREATED)
def create_pricing(pricing_in: ShowCategoryPricingCreate, db: Session = Depends(get_db),current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return show_category_pricing_crud.create(db=db, obj_in=pricing_in)

# -----------------------------
# GET ALL PRICING (with filters)
# -----------------------------
@router.get("/", response_model=List[ShowCategoryPricingOut])
def get_all_pricing(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    show_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    filters = {}
    if show_id:
        filters["show_id"] = show_id
    if category_id:
        filters["category_id"] = category_id
    return show_category_pricing_crud.get_all(db=db, skip=skip, limit=limit, filters=filters)

# -----------------------------
# GET PRICING BY ID
# -----------------------------
@router.get("/{pricing_id}", response_model=ShowCategoryPricingOut)
def get_pricing(pricing_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    pricing = show_category_pricing_crud.get(db=db, id=pricing_id)
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing not found")
    return pricing

# -----------------------------
# UPDATE PRICING
# -----------------------------
@router.put("/{pricing_id}", response_model=ShowCategoryPricingOut)
def update_pricing(pricing_id: int, pricing_in: ShowCategoryPricingUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    db_obj = show_category_pricing_crud.get(db=db, id=pricing_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Pricing not found")
    return show_category_pricing_crud.update(db=db, db_obj=db_obj, obj_in=pricing_in)

# -----------------------------
# DELETE PRICING
# -----------------------------
@router.delete("/{pricing_id}")
def delete_pricing(pricing_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return show_category_pricing_crud.remove(db=db, id=pricing_id)
