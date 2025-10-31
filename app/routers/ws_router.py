from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Optional
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_
from sqlalchemy.orm import Session

from utils.seat_ws_manger import ws_manager

# Existing models
from model.notification import Notification
from model import BookedSeat
from model.seat import SeatLock
from schemas import SeatLockStatus as SeatLockStatusEnum

# Use SessionLocal directly for websocket endpoints (more reliable than Depends in WS).
from database import SessionLocal

router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)

def to_iso(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()

# FIXED: notifications WS uses ws_manager.connect(websocket, user_id) and disconnect(websocket)
@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await ws_manager.connect(websocket, user_id)

    undelivered = await Notification.find({
        "user_id": user_id,
        "delivered": False
    }).to_list()

    for notif in undelivered:
        await websocket.send_text(notif.message)
        await Notification.find({"_id": notif.id}).update({"$set": {"delivered": True}})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)

@router.websocket("/ws/seats/{show_id}")
async def websocket_seats(websocket: WebSocket, show_id: int, user_id: Optional[str] = None):
    # … keep your seat locking implementation here (unchanged) …
    await ws_manager.connect(websocket, user_id)
    await ws_manager.subscribe_show(str(show_id), websocket)
    db: Session = SessionLocal()
    try:
        # handle lock/unlock/extend messages…
        pass
    except WebSocketDisconnect:
        # cleanup…
        await ws_manager.unsubscribe_show(str(show_id), websocket)
        await ws_manager.disconnect(websocket)
    finally:
        try:
            db.close()
        except Exception:
            pass