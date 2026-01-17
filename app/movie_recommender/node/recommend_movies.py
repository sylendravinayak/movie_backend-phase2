from movie_recommender.state import RecState
from database import SessionLocal
from model import Movie

def recommend_movies(state: RecState):
    db = SessionLocal()

    booked_ids = [m.movie_id for m in state["booked_movies"]]

    # normalize user preferred genres
    genres = [g.lower().strip() for g in state["preferred_genres"]]

    movies = (
        db.query(Movie)
        .filter(Movie.movie_id.notin_(booked_ids))
        .all()
    )

    scored = []

    for m in movies:
        if not m.genre:
            continue

        # normalize movie genres (already list)
        m_genres = [g.lower().strip() for g in m.genre]

        score = len(set(m_genres) & set(genres))

        if score > 0:
            scored.append((m, score))

    scored.sort(key=lambda x: (x[1], x[0].rating or 0), reverse=True)

    # fallback when no genre match
    if not scored:
        movies = (
            db.query(Movie)
            .filter(Movie.movie_id.notin_(booked_ids))
            .order_by(Movie.rating.desc())
            .limit(5)
            .all()
        )
        db.close()
        return {"candidates": movies}

    db.close()
    return {"candidates": [m for m, _ in scored[:5]]}
