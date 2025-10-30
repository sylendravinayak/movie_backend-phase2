from crud.base import CRUDBase
from model.food import FoodCategory
from schemas.food_schema import FoodCategoryCreate, FoodCategoryUpdate

food_category_crud = CRUDBase[FoodCategory, FoodCategoryCreate, FoodCategoryUpdate](FoodCategory, id_field="category_id")
