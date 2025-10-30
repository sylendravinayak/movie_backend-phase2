from crud.base import CRUDBase
from model.booking import GST
from schemas.booking_schema import GSTCreate, GSTUpdate

class CRUDGST(CRUDBase[GST, GSTCreate, GSTUpdate]):
    pass

gst_crud = CRUDGST(GST,id_field="gst_id")

