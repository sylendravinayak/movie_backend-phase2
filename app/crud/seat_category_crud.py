from crud.base import CRUDBase
from model import SeatCategory
from schemas.theatre_schema import SeatCategoryCreate, SeatCategoryUpdate

class SeatCategoryCRUD(CRUDBase[SeatCategory, SeatCategoryCreate, SeatCategoryUpdate]):
    def __init__(self):
        super().__init__(SeatCategory, id_field="category_id")

seat_category_crud = SeatCategoryCRUD()
