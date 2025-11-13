from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from schemas.backup_restore import RestoreCreate
from crud.backup_crud import BackupService  # ensure path matches your project layout

router = APIRouter(prefix="/restores", tags=["restores"])


# Dependency that reuses the same DB object as your backups router
def _get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Resolve the motor AsyncIOMotorDatabase from the same module your backups router uses.
    This mirrors the backups router's approach so both routers share the exact same client/db.
    """
    # Import inside the function to avoid import-time side effects and to match backups router pattern
    from database import db as mongo_db 
    return mongo_db


def _get_service(mdb: AsyncIOMotorDatabase = Depends(_get_mongo_db)):
    return BackupService(mdb)




# ----- Routes -----
@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def create_restore(
    payload: RestoreCreate,
    admin_id: int = Query(0, description="ID of the admin/user performing the restore"),
    svc: BackupService = Depends(_get_service),
):
    """
    Trigger a restore operation from a previously completed backup.
    Uses the same Motor DB/client as the backups router via the _get_mongo_db dependency.
    """
    return await svc.restore_backup(payload, admin_id)


@router.get("", response_model=None)
async def list_restores(
    limit: int = Query(50, ge=1, le=500),
    svc: BackupService = Depends(_get_service),
):
    """
    List recent restore operations (most recent first).
    """
    return await svc.list_restores(limit=limit)


@router.get("/{restore_id}", response_model=None)
async def get_restore(
    restore_id: str,
    db: AsyncIOMotorDatabase = Depends(_get_mongo_db),
):
    """
    Fetch a single restore operation by its id using the same DB object as the backups router.
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