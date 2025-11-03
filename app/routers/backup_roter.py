from fastapi import APIRouter, Query
from crud.backup_crud import backup_crud
from schemas.backup_restore import BackupLogCreate, BackupLogUpdate
from utils.backup_service import create_backup


router = APIRouter(prefix="/backup", tags=["Backups"])

@router.post("/")
async def create_backup_log(data: BackupLogCreate):
    return await backup_crud.create(data)

@router.get("/{id}")
async def get_backup(id: str):
    return await backup_crud.get(id)

@router.get("/")
async def get_all(skip: int = 0, limit: int = 10):
    return await backup_crud.get_all(skip=skip, limit=limit)

@router.put("/{id}")
async def update_backup(id: str, data: BackupLogUpdate):
    return await backup_crud.update(id, data)

@router.delete("/{id}")
async def delete_backup(id: str):
    return await backup_crud.remove(id)

# NEW: trigger an actual backup
@router.post("/run")
async def run_backup(
    include_postgres: bool = Query(True, description="Include PostgreSQL backup"),
    include_mongo: bool = Query(True, description="Include MongoDB backup"),
    label: str | None = Query(None, description="Optional label for this backup folder name"),
):
    """
    Creates a timestamped folder under backups/ with:
      - postgres.sql.gz (pg_dump output)
      - mongo.archive.gz (mongodump output)
      - manifest.json (metadata + checksums)
    """
    result = await create_backup(include_postgres=include_postgres, include_mongo=include_mongo, label=label)
    return result