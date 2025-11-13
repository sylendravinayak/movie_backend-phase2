from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import verify_access_token
from database import get_db
from sqlalchemy.orm import Session
from crud.token_crud import is_token_revoked

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request, db: Session = Depends(get_db)):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            # Make scheme check case-insensitive
            if credentials.scheme.lower() != "bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            # Verify access token
            payload = verify_access_token(credentials.credentials)
            if payload is None:
                raise HTTPException(status_code=403, detail="Invalid or expired token.")
            # Check whether this token has been revoked
            jti = payload.get("jti")
            if jti and is_token_revoked(db, jti):
                raise HTTPException(status_code=403, detail="Token has been revoked.")
            return payload
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

def getcurrent_user(role: str):
    def dependency(payload: dict = Depends(JWTBearer())):
        if payload.get("role") != role:
            raise HTTPException(status_code=403, detail="Not authorized")
        return payload
    return dependency