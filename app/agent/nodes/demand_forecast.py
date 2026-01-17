from database import SessionLocal
from model import Movie, Show
from agent.state import OpsState
from agent.tools.forecast_tools import *
from agent.tools.booking_history_tool import (
    get_recent_booking_count,
    get_daily_booking_series
)
from agent.tools.scrapping_tool import google_trend_score
from datetime import date, datetime
from langgraph.errors import NodeInterrupt
from sqlalchemy import text
from datetime import timedelta

def blend_trend(internal_trend, external_trend):
    blended = internal_trend + (external_trend - 1) * 1.2
    return max(0.7, min(round(blended,2),1.3))



def demand_forecast_node(state: OpsState):

    db = SessionLocal()

    movies_to_process = []
    scope = None
    
    

    if state.get("show_id"):
        show = db.query(Show).filter(Show.show_id == state["show_id"]).first()
        if not show:
            db.close()
            raise NodeInterrupt(f"Show {state['show_id']} not found")

        movie = db.query(Movie).filter(Movie.movie_id == show.movie_id).first()
        if not movie:
            db.close()
            raise NodeInterrupt("Movie not found for show")

        movies_to_process = [movie]
        scope = "show"

    elif state.get("movie"):
        movie = db.query(Movie).filter(Movie.title == state["movie"]).first()
        if not movie:
            db.close()
            raise NodeInterrupt("Movie not found for forecasting")

        movies_to_process = [movie]
        scope = "movie"

    elif state.get("movies"):
        movies_to_process = db.query(Movie).filter(
            Movie.title.in_(state["movies"])
        ).all()

        if not movies_to_process:
            db.close()
            raise NodeInterrupt("No movies found for forecasting")

        scope = "movie_list"

    else:
        if state.get("decision", {}).get("route") == "optimize":
            shows = db.query(Show).filter(
                Show.show_date >= date.today()).all()
            if not shows:
                db.close()
                raise NodeInterrupt("No upcoming shows found for forecasting")

            movies_to_process = [db.query(Movie).filter(Movie.movie_id == show.movie_id).first() for show in shows]
            movies_to_process = list(set(movies_to_process))  # Unique movies
        scope ="optimize"
    forecasts = []

    target_date = date.today() + timedelta(days=1)
    titles = [m.title for m in movies_to_process]
    trend_map = google_trend_score(titles)
    for movie in movies_to_process:

        internal = get_recent_booking_count(movie.movie_id, 7, db)
        series = get_daily_booking_series(movie.movie_id, 7, db)
        internal_trend = compute_trend(series)

        external_trend = trend_map.get(movie.title, 0.5)
        external_trend = min(max(external_trend, 0.7), 1.3)

        blended_trend = blend_trend(internal_trend, external_trend)
        

        season = seasonality_factor(datetime.utcnow())
        forecast = forecast_from_trend(blended_trend, season)

        db.execute(text("""
            INSERT INTO forecast_history (movie_id, target_date, forecast_demand)
            VALUES (:movie_id, :target_date, :forecast_demand)
        """), {
            "movie_id": movie.movie_id,
            "target_date": target_date,
            "forecast_demand": forecast
        })


        forecasts.append({
            "movie_id": movie.movie_id,
            "movie_title": movie.title,
            "internal_bookings": internal,
            "internal_trend": internal_trend,
            "external_trend": external_trend,
            "blended_trend": blended_trend,
            "seasonality": season,
            "forecast_demand": forecast,
          
        })


    db.close()

    state.setdefault("result", {})
    state["result"]["forecast"] = forecasts
    state["result"]["forecast_scope"] = scope

    state["output"] = f"Forecast generated for {len(forecasts)} movie(s)."

    return state
