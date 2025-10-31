from model.notification import Notification
from utils.ws_manager import ws_manager

# Sends to all active websocket connections for the user_id.
# Returns True if at least one socket received the message.
async def send_notification(user_id: str | int, message: str) -> bool:
    return await ws_manager.send_personal_message(str(user_id), message)