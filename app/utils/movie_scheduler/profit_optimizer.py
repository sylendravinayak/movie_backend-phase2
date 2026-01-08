from datetime import datetime, timedelta, time
from collections import defaultdict
from model import Screen

# ---------------- CONFIG ----------------

DAY_START = time(9, 0)
DAY_END = time(23, 30)
BUFFER_MIN = 15

PRIME_START = time(18, 0)
PRIME_END = time(22, 0)

MAX_BLOCKBUSTER_RATIO = 0.65
MAX_STREAK = 2


# ---------------- UTILS ----------------

def round_5(t: time) -> time:
    mins = t.hour * 60 + t.minute
    mins = int(5 * round(mins / 5))
    return time(mins // 60, mins % 60)


def is_prime(t: time) -> bool:
    return PRIME_START <= t < PRIME_END


def screen_capacity(screen: Screen) -> int:
    return sum(c.rows * c.cols for c in screen.categories)


# ---------------- DAY SCHEDULER ----------------

def schedule_day_for_screen(movies, screen, show_date):
    cursor = datetime.combine(show_date, DAY_START)
    end_boundary = datetime.combine(show_date, DAY_END)

    movies = sorted(movies, key=lambda m: m["demand_score"], reverse=True)
    top_movie = movies[0]

    usage = defaultdict(int)
    total = 0
    streak = {"movie_id": None, "count": 0}

    shows = []

    while True:
        if cursor >= end_boundary:
            break

        show_time = round_5(cursor.time())
        show_start = datetime.combine(show_date, show_time)

        if show_start >= end_boundary:
            break

        # ---------- MOVIE SELECTION ----------

        if is_prime(show_time):
            movie = top_movie
        else:
            # Least used, but respect streak
            candidates = sorted(
                movies,
                key=lambda m: (usage[m["movie_id"]], -m["demand_score"])
            )

            movie = candidates[0]

            if (
                streak["movie_id"] == movie["movie_id"]
                and streak["count"] >= MAX_STREAK
                and len(candidates) > 1
            ):
                movie = candidates[1]

        # Blockbuster cap
        if (
            movie["movie_id"] == top_movie["movie_id"]
            and total > 0
            and usage[movie["movie_id"]] / total > MAX_BLOCKBUSTER_RATIO
            and not is_prime(show_time)
            and len(movies) > 1
        ):
            movie = movies[1]

        runtime = movie["duration"] + BUFFER_MIN
        end_time = cursor + timedelta(minutes=runtime)

        if end_time > end_boundary:
            break

        # ---------- RECORD ----------

        shows.append({
            "movie_id": movie["movie_id"],
            "screen_id": screen.screen_id,
            "show_date": show_date,
            "show_time": show_time,
            "language": movie["language"],
            "format": movie["format"],
        })

        usage[movie["movie_id"]] += 1
        total += 1

        if streak["movie_id"] == movie["movie_id"]:
            streak["count"] += 1
        else:
            streak["movie_id"] = movie["movie_id"]
            streak["count"] = 1

        cursor = end_time

    return shows


# ---------------- WEEK OPTIMIZER ----------------

def optimize_week(db, movies, start_date):
    screens = db.query(Screen).filter(Screen.is_available == True).all()

    big_screens = [s for s in screens if screen_capacity(s) >= 120]
    small_screens = [s for s in screens if screen_capacity(s) < 120]

    plan = []

    for d in range(7):
        show_date = start_date + timedelta(days=d)

        for screen in big_screens:
            plan.extend(
                schedule_day_for_screen(movies, screen, show_date)
            )

        for screen in small_screens:
            # Reverse priority for small screens
            plan.extend(
                schedule_day_for_screen(
                    sorted(movies, key=lambda m: m["demand_score"]),
                    screen,
                    show_date
                )
            )

    return plan
