from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import verify_token

# The JWTBearer class
class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        # Validating the Scheme : Ensures that the header uses the Bearer scheme (e.g., not “Basic” or something else).
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            # Verifying the token
            ''' Uses verify_token() to decode and validate the JWT.If invalid or expired → raises 403 Forbidden.If valid → returns the payload (e.g., {"sub": "username"}). '''   
            payload = verify_token(credentials.credentials)
            if payload is None:
                raise HTTPException(status_code=403, detail="Invalid or expired token.")
            return payload
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

