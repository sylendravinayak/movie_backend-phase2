from model.notification import Notification
from utils.ws_manager import ws_manager

async def send_notification(user_id: str, message: str):
    delivered = await ws_manager.send_personal_message(user_id, message)

    if not delivered:  
        notif = Notification(
            user_id=user_id,
            message=message,
            notification_type="INFO",
            delivered=False
        )
        await notif.insert()