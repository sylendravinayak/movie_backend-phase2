import os
from dotenv import load_dotenv

load_dotenv()

class Settings():
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/vsms")
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/nexa_cms")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
 
    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

    # SMTP / Email
    SMTP_HOST: str | None = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.getenv("SMTP_USER","sylendravinayak@gmail.com")
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD","aqvw rtne atoy cwbz")
    SMTP_FROM: str | None = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER","admin <sylendravinayak@gmail.com>")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        env_file = ".env"

settings = Settings()