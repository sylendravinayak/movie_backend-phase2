from typing import TypedDict

class RecState(TypedDict):
    user_id: int
    booked_movies: list
    preferred_genres: list
    candidates: list
