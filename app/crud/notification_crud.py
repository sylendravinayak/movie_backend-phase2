from crud.mongo_crud import MongoCRUD
from model.notification import Notification
from schemas.notification_schemas import NotificationCreate, NotificationUpdate

notification_crud = MongoCRUD[Notification, NotificationCreate, NotificationUpdate](Notification)
