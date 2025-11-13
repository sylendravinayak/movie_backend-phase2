from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class BackupType(str, Enum):
    postgres = "postgres"
    mongodb = "mongodb"
    both = "both"


class BackupRequest(BaseModel):
    backupType: BackupType = Field(..., description="Which systems to backup")
    tables: Optional[List[str]] = Field(default=None, description="Postgres tables to include (optional)")
    notes: Optional[str] = Field(default=None, description="Free-form notes for this backup")

# ----- Schemas -----
class RestoreType(str, Enum):
    postgres = "postgres"
    mongodb = "mongodb"
    both = "both"


class RestoreCreate(BaseModel):
    backupId: str = Field(..., description="Mongo ObjectId or identifier of the backup to restore from")
    restoreType: RestoreType = Field(..., description="Which system(s) to restore")
    notes: Optional[str] = Field(None, description="Optional notes for this restore operation")