from __future__ import annotations

from enum import Enum
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from crud.backup_crud import BackupService  # correct import

router = APIRouter(prefix="/backups", tags=["Backups"])
from schemas.backup_restore import BackupRequest  # correct import

def _get_mongo_db():
    # Avoid type-annotating dependencies with third-party types to prevent FastAPI field coercion
    from database import db as mongo_db
    return mongo_db


def _get_service(mdb=Depends(_get_mongo_db)):
    return BackupService(mdb)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_backup(
    body: BackupRequest,
    admin_id: int = Query(0, description="ID of the admin/user performing the backup"),
    svc=Depends(_get_service),
):
    return await svc.create_backup(body, admin_id)


@router.get("/", response_model=None)
async def list_backups(
    limit: int = Query(50, ge=1, le=500),
    svc=Depends(_get_service),
):
    return await svc.list_backups(limit=limit)


@router.get("/{backup_id}", response_model=None)
async def get_backup(
    backup_id: str,
    svc=Depends(_get_service),
):
    return await svc.get_backup(backup_id)


@router.delete("/{backup_id}", response_model=None)
async def delete_backup(
    backup_id: str,
    svc=Depends(_get_service),
):
    return await svc.delete_backup(backup_id)