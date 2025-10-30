import asyncio
from utils.ws_manager import ws_manager
from utils.redis_client import redis_client, STREAM_KEY
from model.notification import Notification
from utils.notification_sender import send_notification

LAST_ID_KEY = "notification_last_id"

async def consume_notifications():
    last_id = await redis_client.get(LAST_ID_KEY) or "0-0"

    while True:
        try:
            messages = await redis_client.xread(
                streams={STREAM_KEY: last_id},
                count=1,
                block=5000
            )
        except Exception as e:
            print("Redis read error:", e)
            await asyncio.sleep(2)
            continue

        if not messages:
            continue

        stream_name, entries = messages[0]

        for msg_id, fields in entries:
            try:
                user_id = fields.get("user_id")
                message = fields.get("message", "")
                notif_type = fields.get("notification_type") or "INFO"

                # ✅ Save to DB
                notif = Notification(
                    user_id=user_id,
                    notification_type=notif_type,
                    message=message,
                    delivered=False
                )
                notif = await notif.create()

                # ✅ Attempt WS send
                delivered = await send_notification(user_id, message)

                # ✅ Update DB delivery flag
                if delivered:
                    await Notification.find({"_id": notif.id}).update({"$set": {"delivered": True}})

                # ✅ Move Redis Offset
                last_id = msg_id
                await redis_client.set(LAST_ID_KEY, last_id)

            except Exception as e:
                print("Consumer error:", e)
