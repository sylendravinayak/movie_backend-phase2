from fastapi import APIRouter, HTTPException, Depends,Query
from typing import Optional
from schemas.movie_schema import MovieCreate, MovieUpdate,MovieOut
from crud.movie_crud import movie_crud
from sqlalchemy.orm import Session
from database import get_db
from typing import Annotated

router = APIRouter(
    prefix="/movies", tags=["movies"]
)

@router.post("/")
def create_movie(movie: MovieCreate, db: Session = Depends(get_db)):
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
def update_movie(movie_id: int, movie_update: MovieUpdate, db: Session = Depends(get_db)):
    db_movie = movie_crud.get(db=db, id=movie_id)
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    updated_movie = movie_crud.update(db=db, db_obj=db_movie, obj_in=movie_update)
    return updated_movie

@router.delete("/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    db_movie = movie_crud.get(db=db, id=movie_id)
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie_crud.delete(db=db, id=movie_id)
    return {"detail": f"Movie with ID {movie_id} deleted successfully"}