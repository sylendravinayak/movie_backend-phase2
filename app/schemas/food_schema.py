from __future__ import annotations

from typing import Optional

from pydantic import Field

from . import ORMModel

# 13. FOOD_CATEGORY
class FoodCategoryBase(ORMModel):
    category_name: str = Field(..., max_length=50)


class FoodCategoryCreate(FoodCategoryBase):
    pass


class FoodCategoryUpdate(ORMModel):
    category_name: Optional[str] = Field(None, max_length=50)


class FoodCategoryOut(FoodCategoryBase):
    category_id: int


# 14. FOOD_ITEM
class FoodItemBase(ORMModel):
    item_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: float
    category_id: int
    is_available: bool = True
    image_url: str = Field(None, max_length=255)
    is_veg: bool = None


class FoodItemCreate(FoodItemBase):
    pass


class FoodItemUpdate(ORMModel):
    item_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=255)
    is_veg: Optional[bool] = None


class FoodItemOut(FoodItemBase):
    food_id: int
    