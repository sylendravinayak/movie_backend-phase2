from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)