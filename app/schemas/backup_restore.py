from pydantic import BaseModel,ConfigDict
from datetime import datetime
from typing import Optional
from model.backup_restore import BackupType, BackupStatus,RestoreStatus


class BackupLogBase(BaseModel):
    backup_type: BackupType
    file_path: str
    size_mb: float


class BackupLogCreate(BackupLogBase):
    completed_at: datetime


class BackupLogUpdate(BaseModel):
    completed_at: Optional[datetime] = None
    status: Optional[BackupStatus] = None


class BackupLogOut(BaseModel):
    id: str
    backup_type: BackupType
    started_at: datetime
    completed_at: datetime
    status: BackupStatus
    file_path: str
    size_mb: float

    model_config = ConfigDict(from_attributes=True)



class RestoreLogBase(BaseModel):
    backup_id: str


class RestoreLogCreate(RestoreLogBase):
    status: Optional[RestoreStatus] = None


class RestoreLogUpdate(BaseModel):
    status: Optional[RestoreStatus] = None


class RestoreLogOut(BaseModel):
    id: str
    backup_id: str
    restored_at: datetime
    status: RestoreStatus

    model_config = ConfigDict(from_attributes=True)
