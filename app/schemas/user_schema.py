from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import  Field,BaseModel,ConfigDict,EmailStr
from . import ORMModel


class UserBase(ORMModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str = Field(..., max_length=15)
    role: str = Field("user", max_length=15)
    model_config=ConfigDict(from_attributes=True)



class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=255)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=255)


class UserOut(UserBase):
    user_id: int = Field(..., ge=1)
    created_at: datetime
