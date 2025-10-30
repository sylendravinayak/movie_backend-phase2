import redis.asyncio as redis
from dotenv import load_dotenv
import os

load_dotenv()

REDIS_URL = "rediss://default:ATKSAAIncDJjNDg3MGYxMGEyNjM0Yzg5YWU0NzEyNzQxMzE3NGIwZHAyMTI5NDY@real-crow-12946.upstash.io:6379"
REDIS_TOKEN ="ATKSAAIncDJjNDg3MGYxMGEyNjM0Yzg5YWU0NzEyNzQxMzE3NGIwZHAyMTI5NDY"

redis_client = redis.from_url(
    REDIS_URL,
    password=REDIS_TOKEN,
    decode_responses=True
)

STREAM_KEY = "notification_stream"
GROUP = "notification_group"
CONSUMER = "fastapi_worker"


async def init_stream_group():
    try:
        await redis_client.xgroup_create(
            STREAM_KEY, GROUP, id="0", mkstream=True
        )
    except Exception:
        pass  # group exists


async def push_notification_event(data: dict):
    await redis_client.xadd(STREAM_KEY, data)
