from crud.base import CRUDBase
from model import ShowCategoryPricing
from schemas.theatre_schema import ShowCategoryPricingCreate, ShowCategoryPricingUpdate
from crud.seat_category_crud import seat_category_crud
from fastapi import HTTPException, status

class ShowCategoryPricingCRUD(CRUDBase[ShowCategoryPricing, ShowCategoryPricingCreate, ShowCategoryPricingUpdate]):

    def create(self, db, obj_in: ShowCategoryPricingCreate):
        # Check if pricing already exists for (show_id, category_id)
        existing = db.query(ShowCategoryPricing).filter(
            ShowCategoryPricing.show_id == obj_in.show_id,
            ShowCategoryPricing.category_id == obj_in.category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pricing already exists for this show and category"
            )
        if obj_in.price==0:
            # Fetch base price from SeatCategory
            category = seat_category_crud.get(db, obj_in.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Seat category not found"
                )
            obj_in.price = category.base_price

        return super().create(db, obj_in)

show_category_pricing_crud = ShowCategoryPricingCRUD(ShowCategoryPricing, id_field="pricing_id")
