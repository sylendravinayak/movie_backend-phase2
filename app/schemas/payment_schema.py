from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field



class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)




class PaymentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    WALLET = "WALLET"




class PaymentBase(ORMModel):
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    transaction_code: str = Field(..., max_length=50)
    amount: int
    refund_amount: Optional[int] = Field(
        default=None, description="Amount refunded, if any"
    )


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(ORMModel):
    payment_status: Optional[PaymentStatus] = None
    refund_amount: Optional[int] = None


class PaymentOut(PaymentBase):
    payment_id: int



