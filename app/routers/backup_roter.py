from fastapi import APIRouter
from crud.backup_crud import backup_crud
from schemas.backup_restore import BackupLogCreate, BackupLogUpdate

router = APIRouter(prefix="/backup", tags=["Backups"])


@router.post("/")
async def create_backup(data: BackupLogCreate):
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
