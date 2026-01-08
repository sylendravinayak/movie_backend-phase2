from crud.base import CRUDBase
from model.booking import Discount
from schemas.booking_schema import DiscountCreate, DiscountUpdate
class DiscountCRUD(CRUDBase[Discount, DiscountCreate, DiscountUpdate]):
    def get_by_code(self, db, code: str) -> Discount:
        return db.query(Discount).filter(Discount.promo_code == code).first()
discount_crud = DiscountCRUD(
    Discount, id_field="discount_id"
)