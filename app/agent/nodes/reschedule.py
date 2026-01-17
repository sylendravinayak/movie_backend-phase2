from datetime import date, timedelta, time
from database import SessionLocal
from model import Show, Seat
from model.theatre import ShowStatusEnum
from model.seat import SeatLock, SeatLockStatusEnum
from agent.state import OpsState

PRIME_START = time(18,0)
PRIME_END   = time(22,0)

def unique_temp_time(show_id: int):
    sec = show_id % 60
    return time(3, 59, sec)

def reschedule_node(state: OpsState):

    db = SessionLocal()
    tomorrow = date.today() + timedelta(days=1)

    forecast_map = {
        f["movie_id"]: f["forecast_demand"]
        for f in state["result"].get("forecast", [])
    }

    shows = db.query(Show).filter(
        Show.show_date == tomorrow,
        Show.status == ShowStatusEnum.UPCOMING
    ).order_by(Show.screen_id, Show.show_time).all()

    result = []

    for show in shows:

        total_seats = db.query(Seat).filter(
            Seat.screen_id == show.screen_id
        ).count() or 1

        booked = db.query(SeatLock).filter(
            SeatLock.show_id == show.show_id,
            SeatLock.status == SeatLockStatusEnum.BOOKED
        ).count()

        occupancy = booked / total_seats
        forecast = forecast_map.get(show.movie_id, 1)

        is_prime = PRIME_START <= show.show_time <= PRIME_END

       
        if occupancy == 0 and forecast <= 1:
            show.status = ShowStatusEnum.CANCELLED
            result.append({"show_id": show.show_id, "action": "cancelled"})
            continue

       
        if forecast >= 3 and not is_prime:

            prime_show = db.query(Show).filter(
                Show.screen_id == show.screen_id,
                Show.show_date == tomorrow,
                Show.show_time >= PRIME_START,
                Show.show_time <= PRIME_END,
                Show.status == ShowStatusEnum.UPCOMING
            ).order_by(Show.show_time).first()

            if prime_show and prime_show.show_id != show.show_id:

                t1 = show.show_time
                t2 = prime_show.show_time

                temp = unique_temp_time(show.show_id)

                show.show_time = temp
                db.flush()

                prime_show.show_time = t1
                db.flush()

                show.show_time = t2

                result.append({
                    "show_id": show.show_id,
                    "action": "swapped_into_prime",
                    "with_show": prime_show.show_id
                })

       
        if forecast <= 1 and is_prime:

            off_show = db.query(Show).filter(
                Show.screen_id == show.screen_id,
                Show.show_date == tomorrow,
                Show.show_time < PRIME_START,
                Show.status == ShowStatusEnum.UPCOMING
            ).order_by(Show.show_time.desc()).first()

            if off_show and off_show.show_id != show.show_id:

                t1 = show.show_time
                t2 = off_show.show_time

                temp = unique_temp_time(show.show_id)

                show.show_time = temp
                db.flush()

                off_show.show_time = t1
                db.flush()

                show.show_time = t2

                result.append({
                    "show_id": show.show_id,
                    "action": "swapped_off_prime",
                    "with_show": off_show.show_id
                })

    db.commit()
    db.close()

    state.setdefault("result", {})
    state["result"]["reschedule"] = result
    state["output"] = f"Safely rescheduled {len(result)} shows."

    return state
