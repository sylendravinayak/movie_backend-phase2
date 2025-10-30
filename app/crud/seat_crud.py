from crud.base import CRUDBase
from model import Seat
from schemas.seat_schema import SeatCreate, SeatUpdate
from sqlalchemy.orm import Session
from typing import List
class SeatCRUD(CRUDBase[Seat, SeatCreate, SeatUpdate]):
    def create(self, db: Session, obj_in_list: List[SeatCreate]) -> List[Seat]:
    
        seats = [Seat(**item.model_dump()) for item in obj_in_list]
        db.add_all(seats)
        db.commit()
        for seat in seats:
            db.refresh(seat)
        return seats  


seat_crud = SeatCRUD(Seat, id_field="seat_id")