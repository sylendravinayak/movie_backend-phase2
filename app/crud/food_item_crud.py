from crud.base import CRUDBase
from model.food import FoodItem
from schemas.food_schema import FoodItemCreate, FoodItemUpdate,FoodItemOut

food_item_crud = CRUDBase[FoodItem, FoodItemCreate, FoodItemUpdate](FoodItem, id_field="food_id")
