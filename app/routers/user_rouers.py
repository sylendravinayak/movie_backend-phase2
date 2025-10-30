from fastapi import APIRouter, HTTPException, Depends, Query
from schemas.user_schema import UserCreate,UserUpdate
from crud.user_crud import user_crud
from sqlalchemy.orm import Session
from database import get_db
router = APIRouter(
    prefix="/users",tags=["users"]
)

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = user_crud.create(db=db, obj_in=user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = user_crud.login(db=db, email=email, password=password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user

@router.get("/")
def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 10, role: str = Query(default="user")):
    users = user_crud.get_all(db=db, skip=skip, limit=limit, filters={"role": role})
    return users

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}")
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = user_crud.get(db=db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = user_crud.update(db=db, db_obj=db_user, obj_in=user_update)
    return updated_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user_crud.get(db=db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_crud.remove(db=db, id=user_id)
    return {"detail": f"User with ID {user_id} deleted successfully"}