from movie_recommender.state import RecState
def extract_genres(state: RecState):
    genres = []

    for m in state["booked_movies"]:
        if m.genre:
            genres.extend(m.genre)

    return {"preferred_genres": list(set(genres))}
