from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from crud.food_item_crud import food_item_crud
from schemas.food_schema import FoodItemCreate, FoodItemUpdate,FoodItemOut as FoodItemResponse
from utils.auth.jwt_bearer import JWTBearer,getcurrent_user
from schemas import UserRole
router = APIRouter(prefix="/food-items", tags=["Food Items"])

# Get all food items with optional filters and pagination
@router.get("/", response_model=List[FoodItemResponse])
def get_all_food_items(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = Query(None, description="Filter by category_id"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    search: str = Query("", description="Filter by name")
):
    filters = {}
    if category_id is not None:
        filters["category_id"] = category_id
    if is_available is not None:
        filters["is_available"] = is_available
    return food_item_crud.get_all( db=db,skip=skip, limit=limit, filters=filters, name=search)

# Get single food item
@router.get("/{food_id}", response_model=FoodItemResponse)
def get_food_item(food_id: int, db: Session = Depends(get_db)):
    item = food_item_crud.get(db, food_id)
    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")
    return item

# Create new food item
@router.post("/", response_model=FoodItemResponse, status_code=status.HTTP_201_CREATED)
def create_food_item(obj_in: FoodItemCreate, db: Session = Depends(get_db), payload:dict=Depends(JWTBearer())):
    return food_item_crud.create(db=db, obj_in=obj_in)

# Update existing food item
@router.put("/{food_id}", response_model=FoodItemResponse)
def update_food_item(food_id: int, obj_in: FoodItemUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    db_obj = food_item_crud.get(db, food_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Food item not found")
    return food_item_crud.update(db, db_obj, obj_in)

# Delete a food item
@router.delete("/{food_id}")
def delete_food_item(food_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    return food_item_crud.remove(db, food_id)
