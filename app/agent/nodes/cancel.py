from datetime import datetime, timedelta
from database import SessionLocal
from model import Show, Seat
from model.theatre import ShowStatusEnum
from model.seat import SeatLock, SeatLockStatusEnum
from agent.state import OpsState


def cancel_node(state: OpsState):

    db = SessionLocal()

    now = datetime.utcnow()

    forecast_map = {
        f["movie_id"]: f["forecast_demand"]
        for f in state["result"]["forecast"]
    }

    shows = db.query(Show).filter(
        Show.status == ShowStatusEnum.UPCOMING
    ).all()

    cancelled = []

    for show in shows:

        show_dt = datetime.combine(show.show_date, show.show_time)
        hours_left = (show_dt - now).total_seconds() / 3600

        total_seats = db.query(Seat).filter(
            Seat.screen_id == show.screen_id
        ).count() or 1

        booked = db.query(SeatLock).filter(
            SeatLock.show_id == show.show_id,
            SeatLock.status == SeatLockStatusEnum.BOOKED
        ).count()

        occupancy = booked / total_seats
        forecast = forecast_map.get(show.movie_id, 1)

        # ---- Cancel logic ----
        if hours_left <= 12 and occupancy < 0.03 and forecast <= 1:
            show.status = ShowStatusEnum.CANCELLED
            cancelled.append(show.show_id)

    db.commit()
    db.close()

    state["result"]["cancelled"] = cancelled
    return state
