from beanie import Document, Link
from typing import Optional
from datetime import datetime

class Notification(Document):
    user_id: int
    booking_id: Optional[int] = None
    notification_type: str
    message: str
    is_read: bool = False
    created_at: datetime = datetime.utcnow()
    read_at: Optional[datetime] = None

    class Settings:
        name = "notifications"  
