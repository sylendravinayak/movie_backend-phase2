import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from utils.auth.jwt_bearer import getcurrent_user,JWTBearer
from database import get_db
from crud.discount_crud import discount_crud
from schemas.booking_schema import DiscountCreate, DiscountUpdate,DiscountOut as DiscountResponse
from schemas import UserRole
from utils.helper import to_utc
router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.post("/", response_model=DiscountResponse)
def create_discount(discount: DiscountCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return discount_crud.create(db, discount)

@router.get("/", response_model=list[DiscountResponse])
def get_all_discounts(db: Session = Depends(get_db),payload:dict=Depends(JWTBearer())):
    return discount_crud.get_all(db)

@router.post("/validate")
def validate_discount(
    code: str,
    movie_id: int = None,
    show_id: int = None,
    amount: float=Query(...), 
    db: Session = Depends(get_db)
):
    discount = discount_crud.get_by_code(db, code)
    code=code.strip().lower()
    if not discount:
        raise HTTPException(status_code=404, detail="Discount code not found")

    now = datetime.datetime.now(datetime.timezone.utc)

    starts_at_utc = to_utc(discount.starts_at)
    ends_at_utc = to_utc(discount.ends_at)

    if starts_at_utc and starts_at_utc > now:
        raise HTTPException(status_code=400, detail="Discount code is not active yet")
    if ends_at_utc and ends_at_utc < now:
        raise HTTPException(status_code=400, detail="Discount code has expired")
    if not discount.is_active:
        raise HTTPException(status_code=400, detail="Discount code is inactive")
    if discount.applicable_movie_id and discount.applicable_movie_id != movie_id:
        raise HTTPException(status_code=400, detail="Discount code is not applicable for this movie")
    if discount.applicable_show_id and discount.applicable_show_id != show_id:
        raise HTTPException(status_code=400, detail="Discount code is not applicable for this show")
    if amount and discount.min_subtotal and amount < discount.min_subtotal:
        raise HTTPException(status_code=400, detail=f"Minimum subtotal of ₹{discount.min_subtotal} required to apply this discount code")
    if discount.discount_type == "percent" and (discount.discount_percent is None or discount.max_discount_amount is None):
        raise HTTPException(status_code=400, detail="Invalid discount configuration for percent type")  
    if discount.discount_type == "flat" and discount.discount_amount is None:       
        raise HTTPException(status_code=400, detail="Invalid discount configuration for flat type") 
    discount_amount=discount.discount_type=="percent" and min((amount * discount.discount_percent) / 100, discount.max_discount_amount) or discount.discount_amount

    return {"isvalid": True, "discount_amount": discount_amount}

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

