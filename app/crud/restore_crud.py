from crud.mongo_crud import MongoCRUD
from model.backup_restore import RestoreLog
from schemas.backup_restore import RestoreLogCreate, RestoreLogUpdate
from model.backup_restore import BackupLog
from fastapi import HTTPException

restore_crud = MongoCRUD[RestoreLog, RestoreLogCreate, RestoreLogUpdate](RestoreLog)

async def create(self, obj_in):
    # Validate referenced backup exists
    backup = await BackupLog.get(obj_in.backup_id)
    if not backup:
        raise HTTPException(status_code=400, detail="Invalid backup_id")
    return await super().create(obj_in)