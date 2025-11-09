from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils.auth.jwt_bearer import getcurrent_user,JWTBearer
from database import get_db
from crud.discount_crud import discount_crud
from schemas.booking_schema import DiscountCreate, DiscountUpdate,DiscountResponse
from schemas import UserRole

router = APIRouter(prefix="/discounts", tags=["Discounts"])

@router.post("/", response_model=DiscountResponse)
def create_discount(discount: DiscountCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return discount_crud.create(db, discount)

@router.get("/", response_model=list[DiscountResponse])
def get_all_discounts(db: Session = Depends(get_db),payload:dict=Depends(JWTBearer())):
    return discount_crud.get_all(db)

@router.get("/{discount_id}", response_model=DiscountResponse)
def get_discount(discount_id: int, db: Session = Depends(get_db), payload: dict = Depends(JWTBearer())):
    record = discount_crud.get(db, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")
    return record

@router.put("/{discount_id}", response_model=DiscountResponse)
def update_discount(discount_id: int, discount: DiscountUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    record = discount_crud.get(db, discount_id)
    if not record:
        raise HTTPException(status_code=404, detail="Discount not found")
    record = discount_crud.update(db, record, discount)
    return record

@router.delete("/{discount_id}")
def delete_discount(discount_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    deleted = discount_crud.remove(db, discount_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"message": "Discount deleted successfully"}
