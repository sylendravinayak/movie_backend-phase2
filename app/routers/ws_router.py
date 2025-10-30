from fastapi import WebSocket, WebSocketDisconnect
from model.notification import Notification
from utils.ws_manager import ws_manager
from fastapi import APIRouter
router = APIRouter()

@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, websocket)

    # ✅ send undelivered messages stored in DB
    undelivered = await Notification.find({
        "user_id": user_id,
        "delivered": False
    }).to_list()

    for notif in undelivered:
        await websocket.send_text(notif.message)
        await Notification.find({"_id": notif.id}).update({"$set": {"delivered": True}})

    try:
        while True:
            # keep connection alive, ignore user messages
            await websocket.receive_text()

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)  # ✅ FIXED
