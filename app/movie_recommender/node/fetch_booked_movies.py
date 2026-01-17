
from movie_recommender.state import RecState
from database import SessionLocal
from model import Movie, Show, Booking

def fetch_booked_movies(state: RecState):
    db = SessionLocal()
    movies = (
    db.query(Movie)
    .join(Show, Show.movie_id == Movie.movie_id)
    .join(Booking, Booking.show_id == Show.show_id)
    .filter(Booking.user_id == state["user_id"])
    .all()
)
    return {"booked_movies": movies}
