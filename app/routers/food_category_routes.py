from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from crud.food_category_crud import food_category_crud
from schemas.food_schema import FoodCategoryCreate, FoodCategoryUpdate,FoodCategoryOut as FoodCategoryResponse
from typing import List
from utils.auth.jwt_bearer import JWTBearer,getcurrent_user
from schemas import UserRole

router = APIRouter(prefix="/food-categories", tags=["Food Categories"])

@router.get("/", response_model=List[FoodCategoryResponse])
def get_all_food_categories(db: Session = Depends(get_db), skip: int = 0, limit: int = 10):
    return food_category_crud.get_all(db=db, skip=skip, limit=limit)

@router.get("/{category_id}", response_model=FoodCategoryResponse)
def get_food_category(category_id: int, db: Session = Depends(get_db)):
    category = food_category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Food Category not found")
    return category

@router.post("/", response_model=FoodCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_food_category(obj_in: FoodCategoryCreate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    foods = food_category_crud.get_all(db=db, skip=0, limit=1000, filters={"category_name": obj_in.category_name})
    if foods:
        raise HTTPException(status_code=400, detail="Food Category already exists")
    return food_category_crud.create(db=db, obj_in=obj_in)

@router.put("/{category_id}", response_model=FoodCategoryResponse)
def update_food_category(category_id: int, obj_in: FoodCategoryUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    db_obj = food_category_crud.get(db, category_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Food Category not found")
    return food_category_crud.update(db, db_obj, obj_in)

@router.delete("/{category_id}")
def delete_food_category(category_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return food_category_crud.remove(db, category_id)
