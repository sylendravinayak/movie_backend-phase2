from crud.base import CRUDBase
from model.booking import Discount
from schemas.booking_schema import DiscountCreate, DiscountUpdate
discount_crud = CRUDBase[Discount, DiscountCreate, DiscountUpdate](
    Discount, id_field="discount_id"
)