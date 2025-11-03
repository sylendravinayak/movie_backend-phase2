from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Column,
    Enum as SAEnum,
    Integer,
    Numeric,
    String,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy import DateTime

# Adjust import to your local Base
# e.g., from payment_service.database import Base
from database import Base  # noqa: F401


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PaymentStatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethodEnum(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    WALLET = "WALLET"


# ---------------------------------------------------------------------------
# 9. PAYMENT
# ---------------------------------------------------------------------------

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_status = Column(SAEnum(PaymentStatusEnum, name="payment_status_enum"), nullable=False)
    payment_method = Column(SAEnum(PaymentMethodEnum, name="payment_method_enum"), nullable=False)
    transaction_code = Column(String(50), nullable=False, unique=True, index=True)
    amount = Column(Integer, nullable=False)
    refund_amount = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


