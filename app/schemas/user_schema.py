from __future__ import annotations

from datetime import datetime
import re
from typing import Optional

from pydantic import  Field,BaseModel,ConfigDict,EmailStr,field_validator
from . import ORMModel


class UserBase(ORMModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str = Field(..., max_length=15)
    role: str = Field("user", max_length=15)
    model_config=ConfigDict(from_attributes=True)



class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=255)
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
        
    


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=255)


class UserOut(UserBase):
    user_id: int = Field(..., ge=1)
    created_at: datetime

class ForgotPasswordRequest(BaseModel):
    """Request password reset link"""
    email: EmailStr = Field(..., description="User's registered email")

class ResetPasswordRequest(BaseModel):
    """Reset password using token from email"""
    token: str = Field(..., min_length=32, description="Password reset token")
    newPassword: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @field_validator('newPassword')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
class ChangePasswordRequest(BaseModel):
    """Change password within app (requires current password)"""
    currentPassword: str = Field(..., description="Current password for verification")
    newPassword: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @field_validator('newPassword')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
