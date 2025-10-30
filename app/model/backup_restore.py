from beanie import Document
from datetime import datetime
from enum import Enum
from pydantic import Field


class BackupType(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"



class BackupStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class BackupLog(Document):
    backup_type: BackupType = Field(...)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime = Field(...)
    status: BackupStatus = Field(default=BackupStatus.SUCCESS)
    file_path: str = Field(..., max_length=255)
    size_mb: float = Field(..., ge=0)

    class Settings:
        name = "backup_logs"


class RestoreStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RestoreLog(Document):
    backup_id: str = Field(..., description="ID of backup used for restore")
    restored_at: datetime = Field(default_factory=datetime.utcnow)
    status: RestoreStatus = Field(default=RestoreStatus.SUCCESS)

    class Settings:
        name = "restore_logs"