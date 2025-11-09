from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from crud.backup_crud import BackupService  # noqa: F401
from utils.auth.jwt_bearer import getcurrent_user

router = APIRouter(prefix="/restores", tags=["restores"])


# ----- Dependencies -----


def get_mongo_db(request: Request) -> AsyncIOMotorDatabase:
    """
    Resolve the motor AsyncIOMotorDatabase from app.state.
    Avoid boolean evaluation of Database objects (they don't implement __bool__).
    """
    db = getattr(request.app.state, "mongo_db", None)
    if db is None:
        db = getattr(request.app.state, "db", None)

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mongo database not initialized on app.state.mongo_db or app.state.db",
        )
    return db


class CurrentUser(BaseModel):
    id: int = Field(..., description="Authenticated admin's user id")


async def get_current_admin(user: Any = Depends(getcurrent_user)) -> CurrentUser:
    """
    Wrap getcurrent_user (which returns a user-like object).
    getcurrent_user now accepts an optional role query param, so absence of ?role won't raise a validation error.
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    uid = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
    try:
        return CurrentUser(id=int(uid))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity")


# ----- Schemas -----


class RestoreType(str, Enum):
    postgres = "postgres"
    mongodb = "mongodb"
    both = "both"


class RestoreCreate(BaseModel):
    backupId: str = Field(..., description="Mongo ObjectId of the backup to restore from")
    restoreType: RestoreType = Field(..., description="Which system(s) to restore")
    notes: Optional[str] = Field(None, description="Optional notes for this restore operation")


# ----- Routes -----


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def create_restore(
    payload: RestoreCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_admin: CurrentUser = Depends(get_current_admin),
):
    """
    Trigger a restore operation from a previously completed backup.
    Returns the created restore record.
    """
    service = BackupService(db=db)
    try:
        result = await service.restore_backup(payload, admin_id=current_admin.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return result


@router.get("", response_model=List[Dict[str, Any]])
async def list_restores(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    List recent restore operations (most recent first).
    """
    service = BackupService(db=db)
    try:
        return await service.list_restores(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{restore_id}", response_model=Dict[str, Any])
async def get_restore(
    restore_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """
    Fetch a single restore operation by its id.
    """
    if not ObjectId.is_valid(restore_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid restore ID")

    try:
        doc = await db.restores.find_one({"_id": ObjectId(restore_id)})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restore not found")

    doc["id"] = str(doc.pop("_id"))
    return doc