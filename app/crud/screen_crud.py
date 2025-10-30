from crud.base import CRUDBase
from model.theatre import Screen
from schemas.theatre_schema import ScreenCreate, ScreenUpdate

class CRUDScreen(CRUDBase[Screen, ScreenCreate, ScreenUpdate]):
    def get_all(self, db, skip: int = 0, limit: int = 10, filters: dict = None):
        query = db.query(Screen)
        
        if filters:
            for attr, value in filters.items():
                if value is None:
                    continue  # skip empty filters

                # custom filter for total_seats
                if attr == "total_seats":
                    query = query.filter(Screen.total_seats >= value)
                
                # generic filter for other valid attributes
                elif hasattr(Screen, attr):
                    query = query.filter(getattr(Screen, attr) == value)
                
                else:
                    # optional safety check
                    raise ValueError(f"Invalid filter field: {attr}")

        return query.offset(skip).limit(limit).all()

screen_crud = CRUDScreen(Screen,id_field="screen_id")
