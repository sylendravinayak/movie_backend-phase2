from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean, Text, Index
from database import Base
# ---------------------------------------------------------------------------
# 12. FOOD_CATEGORY
# ---------------------------------------------------------------------------

class FoodCategory(Base):
    __tablename__ = "food_categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(50), nullable=False, unique=True)


# ---------------------------------------------------------------------------
# 13. FOOD_ITEM
# ---------------------------------------------------------------------------

class FoodItem(Base):
    __tablename__ = "food_items"

    food_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.category_id", ondelete="SET NULL"), nullable=True)
    is_available = Column(Boolean, nullable=False, server_default="true")
    image_url = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_food_items_category_id", "category_id"),
    )

