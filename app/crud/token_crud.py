from sqlalchemy.orm import Session
from model.revoked_token import RevokedToken
from datetime import datetime

def revoke_token(db: Session, jti: str, token_type: str, user_id: int = None):
    if not jti:
        return None
    existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if existing:
        return existing
    rt = RevokedToken(jti=jti, token_type=token_type, user_id=user_id, revoked_at=datetime.utcnow())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt

def is_token_revoked(db: Session, jti: str) -> bool:
    if not jti:
        return False
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None