from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(50), nullable=False)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
