from jose import JWTError, ExpiredSignatureError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from passlib.context import CryptContext
from utils.config import Settings
import uuid

settings = Settings()

def create_access_token(payload: dict) -> str:
    to_encode = payload.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "access"
    })
    token = jwt.encode(to_encode, settings.SECRET_KEY_ACCESS, algorithm=settings.ALGORITHM)
    return token

def create_refresh_token(payload: dict) -> str:
    to_encode = payload.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "refresh"
    })
    token = jwt.encode(to_encode, settings.SECRET_KEY_REFRESH, algorithm=settings.ALGORITHM)
    return token

def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY_ACCESS, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=451, detail="Token has been expired, please login again")
    except JWTError:
        return None
    
def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY_REFRESH, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=451, detail="Refresh token has been expired, please login again")
    except JWTError:
        return None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)