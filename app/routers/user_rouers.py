from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from schemas.user_schema import UserCreate, UserUpdate
from crud.user_crud import user_crud
from sqlalchemy.orm import Session
from utils.auth.jwt_handler import create_access_token, verify_refresh_token
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
from database import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = user_crud.create(db=db, obj_in=user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
def login(response: Response, email: str, password: str, db: Session = Depends(get_db)):
    user = user_crud.login(response=response, db=db, email=email, password=password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user

@router.get("/")
def get_all_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    role: str = Query(default="user"),
    current_user: dict = Depends(getcurrent_user("admin"))
):
    users = user_crud.get_all(db=db, skip=skip, limit=limit, filters={"role": role})
    return users

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(JWTBearer())
):
    # Only owner or admin
    if payload.get("role") != "admin" and payload.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(JWTBearer())
):
    if payload.get("role") != "admin" and payload.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_user = user_crud.get(db=db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = user_crud.update(db=db, db_obj=db_user, obj_in=user_update)
    return updated_user

@router.post("/refresh")
def generate_new_access_token(request: Request, db: Session = Depends(get_db)):
    # Do NOT depend on JWTBearer() here; this route expects a refresh token
    header = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Refresh token missing")
    token = header.split(" ", 1)[1].strip()

    payload = verify_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("user_id")
    role = payload.get("role")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    access_token = create_access_token({"user_id": user_id, "role": role, "email": email})
    return {"access_token": access_token, "token_type": "bearer"}