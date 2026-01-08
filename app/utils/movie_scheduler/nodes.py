from utils.movie_scheduler.imdb_signal_tool import fetch_tmdb_by_imdb_id, compute_demand_from_tmdb,adjust_demand_for_scheduling
from utils.movie_scheduler.profit_optimizer import optimize_week
from model import Show, ShowCategoryPricing, SeatCategory

def fetch_movies_node(state):
    db = state["db"]
    Movie = state["Movie"]

    movies = db.query(Movie).filter(Movie.movie_id.in_(state["movie_ids"])).all()
    return {"movies": movies}

def imdb_signals_node(state):
    enriched = []

    for m in state["movies"]:
        tmdb_movie = fetch_tmdb_by_imdb_id(m.imdb_id)

        if tmdb_movie:
            demand = compute_demand_from_tmdb(tmdb_movie)
            demand = adjust_demand_for_scheduling(demand)

        else:
            demand = 0.001  # safe fallback
            demand = adjust_demand_for_scheduling(demand)

        print(f"Movie ID {m.movie_id} - Demand Score: {demand}")

        enriched.append({
            "movie_id": m.movie_id,
            "title": m.title,
            "duration": m.duration,
            "language": m.language,
            "format": m.format,
            "demand_score": demand,
        })

    return {"movies_with_signals": enriched}

def optimize_node(state):
    plan = optimize_week(
        state["db"],
        state["movies_with_signals"],
        state["start_date"],
    )
    return {"schedule_plan": plan}

def persist_node(state):
    db = state["db"]
    schedule = state["schedule_plan"]

    for i in schedule:
        show = Show(
            movie_id=i["movie_id"],
            screen_id=i["screen_id"],
            show_date=i["show_date"],
            show_time=i["show_time"],
            end_time=i["end_time"],  # optional if you store it
            format=i["format"],
            language=i["language"],
        )

        db.add(show)
        db.flush()  # get show_id

        # Attach pricing
        categories = (
            db.query(SeatCategory)
            .filter(SeatCategory.screen_id == i["screen_id"])
            .all()
        )

        for cat in categories:
            db.add(
                ShowCategoryPricing(
                    show_id=show.show_id,
                    category_id=cat.category_id,
                    price=cat.base_price
                )
            )

    db.commit()
    return {"status": "SHOWS_CREATED"}