from beanie import init_beanie
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from model.backup_restore import BackupLog,RestoreLog
from model.notification import Notification

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:raja807@localhost/movie_booking"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["mydb"]  
async def init_mongo():
    await init_beanie(
        database=db,
        document_models=[BackupLog, RestoreLog,Notification]  
    )