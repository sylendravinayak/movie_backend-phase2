from fastapi import APIRouter, HTTPException, Depends,Query
from typing import Optional
from schemas.movie_schema import MovieCreate, MovieUpdate,MovieOut
from crud.movie_crud import movie_crud
from sqlalchemy.orm import Session
from database import get_db
from typing import Annotated, Dict, Any
from utils.auth.jwt_bearer import JWTBearer,getcurrent_user
from schemas import UserRole
from utils.tmdbclient import TMDBClient, map_tmdb_to_movie_create
router = APIRouter(
    prefix="/movies", tags=["movies"]

)

@router.post("/")
def create_movie(movie: MovieCreate, db: Session = Depends(get_db),current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    new_movie = movie_crud.create(db=db, obj_in=movie)
    return new_movie

def parse_sort_by(sort_by: Optional[str] = Query(
    None,
    description="Comma-separated sorting fields, e.g. rating:desc,release_date:asc"
)):
    
    if not sort_by:
        return None

    sort_dict = {}
    try:
        for item in sort_by.split(","):
            key, direction = item.split(":")
            sort_dict[key.strip()] = direction.strip().lower()
        return sort_dict
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_by format. Use 'field:asc' or 'field:desc' separated by commas."
        )


@router.get("/")
def get_all_movies(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    release_date_from: Optional[str] = None,
    sort_by: Annotated[Optional[dict], Depends(parse_sort_by)] = None
):
    filters = {
        "genre": genre,
        "language": language,
        "release_date_from": release_date_from
    }

    # Clean out None values before passing to CRUD
    filters = {k: v for k, v in filters.items() if v is not None}

    movies = movie_crud.get_all(
        db=db,
        skip=skip,
        limit=limit,
        filters=filters,
        sort_by=sort_by
    )
    return movies

@router.get("/{movie_id}",response_model=MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_crud.get(db=db, id=movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@router.put("/{movie_id}")
def update_movie(movie_id: int, movie_update: MovieUpdate, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    db_movie = movie_crud.get(db=db, id=movie_id)
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    updated_movie = movie_crud.update(db=db, db_obj=db_movie, obj_in=movie_update)
    return updated_movie

@router.delete("/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db),current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    db_movie = movie_crud.get(db=db, id=movie_id)
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie_crud.remove(db=db, id=movie_id)
    return {"detail": f"Movie with ID {movie_id} deleted successfully"}

@router.get("/tmdb/search")
def search_tmdb_movies(
    q: str = Query(..., min_length=2, description="Search query for TMDB (movie title)"),
    page: int = Query(1, ge=1, le=1000, description="Result page number"),
    payload: dict = Depends(JWTBearer())
) -> Dict[str, Any]:
    """
    Search movies on TMDB by title and return a concise list to let users pick one.
    """
    try:
        client = TMDBClient()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = client.search_movies(q, page=page)

    results = []
    for item in data.get("results", []):
        results.append({
            "tmdb_id": item.get("id"),
            "title": item.get("title"),
            "overview": item.get("overview"),
            "release_date": item.get("release_date"),
            "rating_10": item.get("vote_average"),
            "poster_url": TMDBClient.poster_url(item.get("poster_path")),
        })

    return {
        "page": data.get("page"),
        "total_results": data.get("total_results"),
        "total_pages": data.get("total_pages"),
        "results": results,
    }


@router.post("/tmdb/import/{tmdb_id}")
def import_tmdb_movie(
    tmdb_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    """
    Import a single TMDB movie (by tmdb_id) into local DB using MovieCreate schema mapping.
    """
    try:
        client = TMDBClient()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        details = client.get_movie_details(tmdb_id)
    except requests.HTTPError as e:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=f"TMDB error: {e}")  # bubble up TMDB error

    mapped = map_tmdb_to_movie_create(details)

    if not mapped.get("title"):
        raise HTTPException(status_code=400, detail="TMDB movie has no title; cannot import.")

    # Create the movie
    movie = movie_crud.create(db=db, obj_in=MovieCreate(**mapped))
    return movie

