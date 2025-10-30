from crud.base import CRUDBase
from model import Booking
from schemas.booking_schema import BookingCreate, BookingUpdate

booking_crud = CRUDBase[Booking, BookingCreate, BookingUpdate](
    Booking, id_field="booking_id"
)
