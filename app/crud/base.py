from typing import Generic, TypeVar, Type, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi import HTTPException, status

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], id_field: str = "id"):
        self.model = model
        self.id_field = id_field

    # ---------------- GET ----------------
    def get(self, db: Session, id: int) -> ModelType:
        pk_column = getattr(self.model, self.id_field)
        obj = db.query(self.model).filter(pk_column == id).first()
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with {self.id_field}={id} not found"
            )
        return obj

    # ---------------- GET ALL ----------------
    def get_all(self, db: Session, skip=0, limit=10, filters=None):
        query = db.query(self.model)
        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        data = query.offset(skip).limit(limit).all()
        return data

    # ---------------- CREATE ----------------
    def create(self, db: Session, obj_in: CreateSchemaType):
        obj = self.model(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # ---------------- UPDATE ----------------
    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType):
        if not db_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} not found for update"
            )
        update_data = obj_in.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # ---------------- DELETE ----------------
    def remove(self, db: Session, id: int):
        pk_column = getattr(self.model, self.id_field)
        obj = db.query(self.model).filter(pk_column == id).first()
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with {self.id_field}={id} not found"
            )
        db.delete(obj)
        db.commit()
        return {"detail": f"{self.model.__name__} deleted successfully"}
