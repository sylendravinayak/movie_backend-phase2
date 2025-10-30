from crud.base import CRUDBase as BaseCRUD
from model import BookedSeat
from schemas.booking_schema import BookedSeatCreate, BookedSeatUpdate,BookedSeatOut as BookedSeatResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
class BookedSeatCRUD(BaseCRUD[BookedSeat, BookedSeatCreate, BookedSeatUpdate]):
    pass
booked_seat_crud = BookedSeatCRUD(BookedSeat,id_field="booked_seat_id")