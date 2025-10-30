from crud.base import CRUDBase
from model.movie import Movie
from schemas.movie_schema import MovieCreate, MovieUpdate
from sqlalchemy.orm import Session

class CRUDMovie(CRUDBase[Movie, MovieCreate, MovieUpdate]):
    def get_all(self, db: Session, skip=0, limit=10, filters=None, sort_by=None):
        query = db.query(Movie)
        if filters:
            for attr, value in filters.items():
                if attr == "genre" and value:
                    query = query.filter(Movie.genre.any(value))
                if attr == "language" and value:
                    query = query.filter(Movie.language.any(value))
                if attr == "release_date_from" and value:
                    query = query.filter(Movie.release_date >= value)
        if sort_by:
             for attr, direction in sort_by.items():
                if hasattr(Movie, attr):
                    column = getattr(Movie, attr)
                    if direction.lower() == "desc":
                        query = query.order_by(column.desc())
                    else:
                        query = query.order_by(column.asc())
        return query.offset(skip).limit(limit).all()
movie_crud = CRUDMovie(Movie, id_field="movie_id")