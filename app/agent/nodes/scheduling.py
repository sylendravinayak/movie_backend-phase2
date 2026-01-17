from datetime import timedelta, date, time, datetime
from collections import defaultdict
from app.agent.state import OpsState
from database import SessionLocal
from model import Show, Movie, Screen, Seat
from model.theatre import ShowStatusEnum
from agent.tools.scheduling_tool import generate_day_slots, is_prime_slot

OPEN_TIME = time(9,0)
CLOSE_TIME = time(23,0)
BUFFER_MIN = 20
DAYS = 7
MAX_SHOWS_PER_MOVIE_PER_DAY = 3


def round_to_5(t: time):
    dt0 = datetime.combine(date.today(), t)
    m = round(dt0.minute / 5) * 5
    return (dt0.replace(minute=0, second=0) + timedelta(minutes=m)).time()


def scheduling_node(state: OpsState):

    db = SessionLocal()

    start_date = date.today() + timedelta(days=1)

    scheduled_output = []
    scheduled_ids = []

    forecast_list = state.get("result", {}).get("forecast", [])
    if not forecast_list:
        raise Exception("Forecast data missing")

    forecast_map = {f["movie_id"]: f["forecast_demand"] for f in forecast_list}

    screens = db.query(Screen).filter(Screen.is_available == True).all()

    # Screen capacity
    capacity_map = {
        s.screen_id: db.query(Seat).filter(Seat.screen_id == s.screen_id).count() or 1
        for s in screens
    }

    max_capacity = max(capacity_map.values())

    for screen in screens:

        capacity_weight = capacity_map[screen.screen_id] / max_capacity

        for d in range(DAYS):

            show_date = start_date + timedelta(days=d)

            # Clear old upcoming
            db.query(Show).filter(
                Show.screen_id==screen.screen_id,
                Show.show_date==show_date,
                Show.status==ShowStatusEnum.UPCOMING
            ).delete()

            # ---- SLOT GENERATION ----
            slots = generate_day_slots(
                OPEN_TIME, CLOSE_TIME,
                timedelta(minutes=120),
                BUFFER_MIN
            )

            slots = [round_to_5(s) for s in slots]

            prime_slots = [s for s in slots if is_prime_slot(s)]
            normal_slots = [s for s in slots if not is_prime_slot(s)]

            # ---- DEMAND QUOTA ----
            total_demand = sum(forecast_map.values())

            quotas = {}
            for movie_id, demand in forecast_map.items():
                quotas[movie_id] = max(
                    1,
                    round((demand / total_demand) * len(slots))
                )

            # Cap monopoly
            for k in quotas:
                quotas[k] = min(quotas[k], MAX_SHOWS_PER_MOVIE_PER_DAY)

            movie_counter = defaultdict(int)

            # ---- ASSIGN PRIME FIRST ----
            for slot in prime_slots:

                best_movie = max(
                    quotas.keys(),
                    key=lambda m: (quotas[m] - movie_counter[m]) * forecast_map[m]
                )

                if movie_counter[best_movie] >= quotas[best_movie]:
                    continue

                movie = db.query(Movie).filter(Movie.movie_id==best_movie).first()
                if not movie:
                    continue

                end_time = (
                    datetime.combine(show_date, slot) +
                    timedelta(minutes=movie.duration)
                ).time()

                new_show = Show(
                    movie_id=movie.movie_id,
                    screen_id=screen.screen_id,
                    show_date=show_date,
                    show_time=slot,
                    end_time=end_time,
                    status=ShowStatusEnum.UPCOMING,
                    format="2D",
                    language=movie.language[0] if movie.language else "English"
                )

                db.add(new_show)
                db.flush()

                movie_counter[movie.movie_id] += 1

                scheduled_output.append({
                    "show_id": new_show.show_id,
                    "screen": screen.screen_name,
                    "movie": movie.title,
                    "date": str(show_date),
                    "time": slot.strftime("%H:%M"),
                    "forecast_demand": forecast_map[movie.movie_id],
                    "capacity_weight": round(capacity_weight,2)
                })

                scheduled_ids.append(new_show.show_id)

            # ---- ASSIGN NORMAL ----
            for slot in normal_slots:

                for movie_id in quotas:

                    if movie_counter[movie_id] >= quotas[movie_id]:
                        continue

                    movie = db.query(Movie).filter(Movie.movie_id==movie_id).first()
                    if not movie:
                        continue

                    end_time = (
                        datetime.combine(show_date, slot) +
                        timedelta(minutes=movie.duration)
                    ).time()

                    new_show = Show(
                        movie_id=movie.movie_id,
                        screen_id=screen.screen_id,
                        show_date=show_date,
                        show_time=slot,
                        end_time=end_time,
                        status=ShowStatusEnum.UPCOMING,
                        format="2D",
                        language=movie.language[0] if movie.language else "English"
                    )

                    db.add(new_show)
                    db.flush()

                    movie_counter[movie.movie_id] += 1

                    scheduled_output.append({
                        "show_id": new_show.show_id,
                        "screen": screen.screen_name,
                        "movie": movie.title,
                        "date": str(show_date),
                        "time": slot.strftime("%H:%M"),
                        "forecast_demand": forecast_map[movie.movie_id],
                        "capacity_weight": round(capacity_weight,2)
                    })

                    scheduled_ids.append(new_show.show_id)
                    break

    db.commit()
    db.close()

    state.setdefault("result", {})
    state["result"]["scheduling"] = scheduled_output
    state["result"]["scheduled_show_ids"] = scheduled_ids

    state["output"] = f"{len(scheduled_output)} shows scheduled cleanly with demand quota strategy."

    return state
