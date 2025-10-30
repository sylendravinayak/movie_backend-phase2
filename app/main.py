from fastapi import FastAPI
from utils.middleware.authentication_middleware import AuthorizationMiddleware
from routers.user_rouers import router as user_router
from routers.movie_router import router as movie_router
from routers.screen_router import router as screen_router
from routers.seat_rouer import router as seat_router
from routers.seat_category_routes import router as seat_category_router
from routers.show_router import router as show_router
from routers.show_category_pricing_schema import router as show_category_pricing_router
from database import SessionLocal, engine, Base, init_mongo
import asyncio
from sqlalchemy.orm import Session
from crud.seat_lock_crud import SeatLockCRUD
from routers.seat_lock_routes import router as seat_lock_router
from routers.payment_routes import router as payment_router
from routers.food_category_routes import router as food_category_router
from routers.food_item_routes import router as food_item_router
from routers.discount_routes import router as discount_router
from routers.gst_routes import router as gst_router
from routers.booking_routes import router as booking_router
from routers.booked_seat_routes import router as booked_seat_router
from routers.backup_roter import router as backup_router
from routers.restore_router import router as restore_router
from utils.redis_client import init_stream_group
from utils.notification_consumer import consume_notifications
from model.notification import Notification
from routers.notification_router import router as notification_router
from routers.ws_router import router as ws_router
Base.metadata.create_all(bind=engine)
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

seatlock_crud = SeatLockCRUD()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.middleware("http")
async def allow_ws(request, call_next):
    if "upgrade" in request.headers.get("connection", "").lower() and \
       request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)
    return await call_next(request)


async def cleanup_task():
    while True:
        db: Session = SessionLocal()
        count = seatlock_crud.release_expired_locks(db)
        db.close()
        print(f"[Cleanup] Released {count} expired seat locks")
        await asyncio.sleep(6000000)  # every 10 minutes

@app.on_event("startup")
async def startup_event():
    await init_mongo()
    await init_stream_group()
    asyncio.create_task(consume_notifications())

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_task())

app.include_router(user_router)
app.include_router(movie_router)
app.include_router(screen_router)
app.include_router(seat_router)
app.include_router(seat_category_router)
app.include_router(show_router)
app.include_router(show_category_pricing_router)   
app.include_router(seat_lock_router) 
app.include_router(payment_router)
app.include_router(food_category_router)
app.include_router(food_item_router)
app.include_router(discount_router)
app.include_router(gst_router)
app.include_router(booking_router)
app.include_router(booked_seat_router)
app.include_router(backup_router)
app.include_router(restore_router)
app.include_router(notification_router)
app.include_router(ws_router)
