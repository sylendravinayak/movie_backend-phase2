from typing import Generic, TypeVar, Type, Optional, Dict, Any, List
from beanie import Document
from pydantic import BaseModel
from fastapi import HTTPException, status

ModelType = TypeVar("ModelType", bound=Document)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class MongoCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    # -------- GET BY ID --------
    async def get(self, id: str) -> ModelType:
        obj = await self.model.get(id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with id={id} not found"
            )
        return obj

    # -------- GET ALL with filters --------
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:

        query = self.model.find(filters or {})
        return await query.skip(skip).limit(limit).to_list()

    # -------- CREATE --------
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        obj = self.model(**obj_in.dict())
        await obj.insert()
        return obj

    # -------- UPDATE --------
    async def update(self, id: str, obj_in: UpdateSchemaType) -> ModelType:
        obj = await self.get(id)
        update_data = obj_in.dict(exclude_unset=True)

        await obj.set(update_data)
        return obj

    # -------- DELETE --------
    async def remove(self, id: str):
        obj = await self.get(id)
        await obj.delete()
        return {"detail": f"{self.model.__name__} deleted successfully"}
