from fastapi import APIRouter, Query
from schemas.notification_schemas import NotificationCreate, NotificationUpdate
from crud.notification_crud import notification_crud
from model.notification import Notification
from utils.redis_client import push_notification_event
router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/")
async def create_notification(data: NotificationCreate):
    return await notification_crud.create(data)

@router.get("/")
async def get_notifications(
    skip: int = 0,
    limit: int = 10,
    user_id: int | None = Query(None)
):
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    return await notification_crud.get_all(skip=skip, limit=limit, filters=filters)

@router.get("/notify")
async def test_notification(user_id: str, msg: str):
    await push_notification_event({
        "user_id": user_id,
        "notification_type": "TEST",
        "message": msg
    })
    return {"status": "notification sent to stream"}


@router.get("/{id}")
async def get_notification(id: str):
    return await notification_crud.get(id)

@router.patch("/{id}")
async def update_notification(id: str, data: NotificationUpdate):
    return await notification_crud.update(id, data)

@router.delete("/{id}")
async def delete_notification(id: str):
    return await notification_crud.remove(id)

@router.post("/mark-all-read/{user_id}")
async def mark_all_read(user_id: str):
    await Notification.find({"user_id": user_id}).update({"$set": {"is_read": True}})
    return {"detail": "All notifications marked read"}
