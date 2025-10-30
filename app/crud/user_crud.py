from crud.base import CRUDBase
from model.user import User
from schemas.user_schema import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from utils.auth.jwt_handler import verify_password, hash_password,create_access_token,create_refresh_token
from typing import Optional
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, obj_in: UserCreate) -> User:
        existing_user = db.query(User).filter((User.email == obj_in.email) | (User.phone == obj_in.phone)).first()
        if existing_user:
            raise ValueError("A user with this email or phone number already exists.")
        new_user = User(
            email=obj_in.email,
            phone=obj_in.phone,
            name=obj_in.name,
            role=obj_in.role,
            password=hash_password(obj_in.password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    
    def login(self,db: Session,email:str,password:str)->User:
        user = db.query(User).filter(User.email == email).first()
        if user and verify_password(password, user.password):
            token_data = {
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role
            }
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
    

user_crud = CRUDUser(User,id_field="user_id")