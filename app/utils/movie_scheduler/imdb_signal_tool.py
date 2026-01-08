import requests
import os

TMDB_API_KEY = os.getenv("TMDB_API_KEY","c03f10ce149f5b0b162742943632938f")

TMDB_BASE = "https://api.themoviedb.org/3"


def normalize(value, max_val):
    if not value or value <= 0:
        return 0.0
    return min(value / max_val, 1.0)


def fetch_tmdb_by_imdb_id(imdb_id: str) -> dict | None:
    """
    Fetch TMDB movie using IMDb ID.
    Returns TMDB movie dict or None.
    """

    if not imdb_id:
        return None

    imdb_id = imdb_id.strip().lower()
    if not imdb_id.startswith("tt"):
        imdb_id = f"tt{imdb_id}"

    url = f"{TMDB_BASE}/find/{imdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "external_source": "imdb_id"
    }

    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    # Movies are here
    movies = data.get("movie_results", [])
    if not movies:
        return None

    return movies[0]  # best match


def compute_demand_from_tmdb(tmdb_movie: dict) -> float:
    """
    Production demand score (0–1).
    """

    popularity = tmdb_movie.get("popularity", 0)
    vote_count = tmdb_movie.get("vote_count", 0)
    vote_avg = tmdb_movie.get("vote_average", 0)

    pop_score = normalize(popularity, 500)
    vote_score = normalize(vote_count, 10000)
    rating_score = vote_avg / 10

    print(f"TMDB Popularity: {popularity}, Vote Count: {vote_count}, Vote Avg: {vote_avg}")
    demand = (
        0.5 * pop_score +
        0.3 * vote_score +
        0.2 * rating_score
    )

    
 
    # 🚨 IMPORTANT FIX
    # Apply floor ONLY if absolutely no signal exists
    if popularity == 0 and vote_count == 0 and vote_avg == 0:
        return 0.12
    return round(demand, 3)
def adjust_demand_for_scheduling(demand: float) -> float:
    """
    Compress extreme values into a scheduling-friendly range.
    Preserves ordering.
    """
    if demand <= 0:
        return 0.15

    # Log compression
    adjusted = 0.2 + (demand ** 0.5) * 0.6

    return round(min(adjusted, 0.95), 3)
