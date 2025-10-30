from fastapi import APIRouter
from crud.restore_crud import restore_crud
from schemas.backup_restore import RestoreLogCreate, RestoreLogUpdate

router = APIRouter(prefix="/restore", tags=["Restore Logs"])


@router.post("/")
async def create_restore(data: RestoreLogCreate):
    return await restore_crud.create(data)


@router.get("/{id}")
async def get_restore(id: str):
    return await restore_crud.get(id)


@router.get("/")
async def get_all(skip: int = 0, limit: int = 10):
    return await restore_crud.get_all(skip=skip, limit=limit)


@router.put("/{id}")
async def update_restore(id: str, data: RestoreLogUpdate):
    return await restore_crud.update(id, data)


@router.delete("/{id}")
async def delete_restore(id: str):
    return await restore_crud.remove(id)
