from requests import Session
from crud.base import CRUDBase
from model.food import FoodCategory, FoodItem
from schemas.food_schema import FoodItemCreate, FoodItemUpdate,FoodItemOut

class FoodItemCRUD(CRUDBase[FoodItem, FoodItemCreate, FoodItemUpdate]):
      def get_all(self,db: Session, skip: int, limit: int, filters: dict,name:str):
        query = db.query(FoodItem).join(FoodCategory, isouter=True)
        if name:
            query = query.filter(FoodItem.item_name.ilike(f"%{name}%"))
        for key, value in filters.items():
            query = query.filter(getattr(FoodItem, key) == value)

        items = query.offset(skip).limit(limit).all()
        return items
  

food_item_crud = FoodItemCRUD(FoodItem, id_field="food_id")