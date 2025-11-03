from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Optional
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_
from sqlalchemy.orm import Session

# Use the unified manager
from utils.ws_manager import ws_manager

# Models
from model.notification import Notification
from model import BookedSeat
from model.seat import SeatLock
from schemas import SeatLockStatus as SeatLockStatusEnum

# Use SessionLocal directly for WS endpoints
from database import SessionLocal

router = APIRouter()

def utcnow():
    return datetime.now(timezone.utc)

def to_iso(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()

@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await ws_manager.connect(websocket, user_id)

    undelivered = await Notification.find({
        "user_id": int(user_id),
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
    # Accept and subscribe
    await ws_manager.connect(websocket, user_id)
    await ws_manager.subscribe_show(str(show_id), websocket)

    # Parse user_id for DB ownership
    parsed_user_id: Optional[int] = None
    try:
        if user_id is not None and str(user_id).strip() != "":
            parsed_user_id = int(str(user_id).strip())
    except Exception:
        parsed_user_id = None

    db: Session = SessionLocal()
    try:
        async def send_error(msg: str):
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": msg}))
            except Exception:
                pass

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                await send_error("Invalid JSON")
                continue

            action = data.get("action")

            if action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if action not in {"lock", "unlock", "extend"}:
                await send_error("Unsupported action")
                continue

            seat_id = data.get("seat_id")
            if not isinstance(seat_id, int):
                await send_error("seat_id must be an integer")
                continue

            if parsed_user_id is None:
                await send_error("user_id is required and must be a number to lock/extend/unlock seats")
                continue

            # already booked?
            booked_row = db.query(BookedSeat).filter(
                and_(BookedSeat.show_id == int(show_id), BookedSeat.seat_id == seat_id)
            ).first()
            if booked_row and action in {"lock", "extend"}:
                await websocket.send_text(json.dumps({
                    "type": "seat_booked",
                    "show_id": int(show_id),
                    "seat_ids": [seat_id],
                    "booking_id": getattr(booked_row, "booking_id", None)
                }))
                continue

            now = utcnow()

            if action == "lock":
                ttl = int(data.get("ttl", 30))
                expires_at = now + timedelta(seconds=max(5, ttl))

                active_lock = db.query(SeatLock).filter(
                    SeatLock.show_id == int(show_id),
                    SeatLock.seat_id == seat_id,
                    SeatLock.status == SeatLockStatusEnum.LOCKED,
                    SeatLock.expires_at > now
                ).first()
                if active_lock:
                    await send_error(f"Seat {seat_id} is already locked")
                    continue

                new_lock = SeatLock(
                    show_id=int(show_id),
                    seat_id=seat_id,
                    user_id=parsed_user_id,
                    status=SeatLockStatusEnum.LOCKED,
                    expires_at=expires_at
                )
                db.add(new_lock)
                db.commit()
                db.refresh(new_lock)

                await ws_manager.add_ws_lock(websocket, str(show_id), seat_id)

                await ws_manager.broadcast_to_show(str(show_id), {
                    "type": "seat_lock",
                    "show_id": int(show_id),
                    "seat_id": seat_id,
                    "locked_by": parsed_user_id,
                    "expires_at": to_iso(expires_at)
                })

            elif action == "unlock":
                # Only owner unlocks
                lock = db.query(SeatLock).filter(
                    SeatLock.show_id == int(show_id),
                    SeatLock.seat_id == seat_id,
                    SeatLock.user_id == parsed_user_id,
                    SeatLock.status == SeatLockStatusEnum.LOCKED,
                    SeatLock.expires_at > now
                ).first()
                if lock:
                    db.delete(lock)
                    db.commit()

                await ws_manager.remove_ws_lock(websocket, str(show_id), seat_id)

                await ws_manager.broadcast_to_show(str(show_id), {
                    "type": "seat_unlock",
                    "show_id": int(show_id),
                    "seat_id": seat_id
                })

            elif action == "extend":
                ttl = int(data.get("ttl", 30))
                new_expiry = now + timedelta(seconds=max(5, ttl))

                lock = db.query(SeatLock).filter(
                    SeatLock.show_id == int(show_id),
                    SeatLock.seat_id == seat_id,
                    SeatLock.user_id == parsed_user_id,
                    SeatLock.status == SeatLockStatusEnum.LOCKED,
                    SeatLock.expires_at > now
                ).first()
                if not lock:
                    await send_error(f"No active lock to extend for seat {seat_id}")
                    continue

                lock.expires_at = new_expiry
                db.add(lock)
                db.commit()

                await ws_manager.broadcast_to_show(str(show_id), {
                    "type": "seat_lock",
                    "show_id": int(show_id),
                    "seat_id": seat_id,
                    "locked_by": parsed_user_id,
                    "expires_at": to_iso(new_expiry)
                })

    except WebSocketDisconnect:
        # On disconnect, delete locks held by this socket
        held = await ws_manager.get_ws_locks(websocket)
        now = utcnow()
        for (s_show_id, s_seat_id) in held:
            lock = db.query(SeatLock).filter(
                SeatLock.show_id == int(s_show_id),
                SeatLock.seat_id == int(s_seat_id),
                SeatLock.status == SeatLockStatusEnum.LOCKED,
                SeatLock.expires_at > now
            ).first()
            if lock:
                db.delete(lock)
                db.commit()
                await ws_manager.broadcast_to_show(str(s_show_id), {
                    "type": "seat_unlock",
                    "show_id": int(s_show_id),
                    "seat_id": int(s_seat_id)
                })
        await ws_manager.unsubscribe_show(str(show_id), websocket)
        await ws_manager.disconnect(websocket)
    finally:
        try:
            db.close()
        except Exception:
            pass