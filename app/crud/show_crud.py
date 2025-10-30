from crud.base import CRUDBase
from model import Show
from schemas.theatre_schema import ShowCreate, ShowUpdate

class ShowCRUD(CRUDBase[Show, ShowCreate, ShowUpdate]):
    pass

show_crud = ShowCRUD(Show, id_field="show_id")
