from crud.base import CRUDBase
from model.booking import GST
from schemas.booking_schema import GSTCreate, GSTUpdate

class CRUDGST(CRUDBase[GST, GSTCreate, GSTUpdate]):
    def get_by_category(self, db, category: str):
        return db.query(self.model).filter(self.model.category == category).first()

gst_crud = CRUDGST(GST,id_field="gst_id")

