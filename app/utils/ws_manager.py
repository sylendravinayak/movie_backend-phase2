from typing import Dict, List
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, set] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket):
        for uid, sockets in list(self.active_connections.items()):
            if websocket in sockets:
                sockets.remove(websocket)
                if not sockets:
                    del self.active_connections[uid]
                break

    async def send_personal_message(self, user_id: str, message: str):
        sockets = self.active_connections.get(user_id, [])
        if not sockets:
            return False

        for ws in list(sockets):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)
        return True

ws_manager = WebSocketManager()
