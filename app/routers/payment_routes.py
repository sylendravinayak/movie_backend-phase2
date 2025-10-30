from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.payment_schema import PaymentCreate, PaymentUpdate,PaymentOut as PaymentResponse
from crud.payment_crud import payment_crud
from database import get_db

router = APIRouter(prefix="/payments", tags=["Payments"])



@router.post("/", response_model=PaymentResponse)
def create_payment(obj_in: PaymentCreate, db: Session = Depends(get_db)):
    return payment_crud.create(db, obj_in)


@router.get("/", response_model=list[PaymentResponse])
def get_all_payments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return payment_crud.get_all(db, skip, limit)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_crud.get(db, payment_id)


@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(payment_id: int, obj_in: PaymentUpdate, db: Session = Depends(get_db)):
    db_obj = payment_crud.get(db, payment_id)
    return payment_crud.update(db, db_obj, obj_in)


@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_crud.remove(db, payment_id)
