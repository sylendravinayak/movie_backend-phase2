from crud.mongo_crud import MongoCRUD
from model.backup_restore import BackupLog
from schemas.backup_restore import BackupLogCreate, BackupLogUpdate

backup_crud = MongoCRUD[BackupLog, BackupLogCreate, BackupLogUpdate](BackupLog)
