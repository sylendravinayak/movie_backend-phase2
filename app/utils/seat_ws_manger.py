from typing import Dict, Set, Tuple
from fastapi import WebSocket
import asyncio
import json

class WebSocketManager:
    def __init__(self):
        # user_id -> set(WebSocket)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # show_id -> set(WebSocket)
        self.show_subscriptions: Dict[str, Set[WebSocket]] = {}
        # ws -> set of (show_id, seat_id)
        self.ws_held_locks: Dict[WebSocket, Set[Tuple[str, int]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str | None = None):
        await websocket.accept()
        async with self._lock:
            if user_id:
                self.active_connections.setdefault(str(user_id), set()).add(websocket)
            self.ws_held_locks.setdefault(websocket, set())

    async def subscribe_show(self, show_id: str, websocket: WebSocket):
        async with self._lock:
            self.show_subscriptions.setdefault(str(show_id), set()).add(websocket)

    async def unsubscribe_show(self, show_id: str, websocket: WebSocket):
        async with self._lock:
            sockets = self.show_subscriptions.get(str(show_id), set())
            if websocket in sockets:
                sockets.remove(websocket)
                if not sockets:
                    del self.show_subscriptions[str(show_id)]

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            for uid, sockets in list(self.active_connections.items()):
                if websocket in sockets:
                    sockets.remove(websocket)
                    if not sockets:
                        del self.active_connections[uid]
                    break
            for show_id, sockets in list(self.show_subscriptions.items()):
                if websocket in sockets:
                    sockets.remove(websocket)
                    if not sockets:
                        del self.show_subscriptions[show_id]
            if websocket in self.ws_held_locks:
                del self.ws_held_locks[websocket]

    async def broadcast_to_show(self, show_id: str, message_obj):
        payload = message_obj if isinstance(message_obj, str) else json.dumps(message_obj)
        sockets = list(self.show_subscriptions.get(str(show_id), set()))
        any_sent = False
        for ws in sockets:
            try:
                await ws.send_text(payload)
                any_sent = True
            except Exception:
                await self.disconnect(ws)
        return any_sent

    async def add_ws_lock(self, websocket: WebSocket, show_id: str, seat_id: int):
        async with self._lock:
            self.ws_held_locks.setdefault(websocket, set()).add((str(show_id), int(seat_id)))

    async def remove_ws_lock(self, websocket: WebSocket, show_id: str, seat_id: int):
        async with self._lock:
            held = self.ws_held_locks.get(websocket, set())
            held.discard((str(show_id), int(seat_id)))

    async def get_ws_locks(self, websocket: WebSocket):
        async with self._lock:
            return set(self.ws_held_locks.get(websocket, set()))

ws_manager = WebSocketManager()