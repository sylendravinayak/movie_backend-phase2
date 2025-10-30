from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from model.payments import Payment
from schemas.payment_schema import PaymentCreate, PaymentUpdate

from crud.base import CRUDBase

class PaymentCRUD(CRUDBase[Payment, PaymentCreate, PaymentUpdate]):
    pass
payment_crud = PaymentCRUD(Payment, id_field="payment_id")