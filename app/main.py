from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from model.backup_restore import BackupLog, RestoreLog
from utils.middleware.authentication_middleware import AuthorizationMiddleware
from routers.user_routers import router as user_router
from routers.movie_router import router as movie_router
from routers.screen_router import router as screen_router
from routers.seat_router import router as seat_router
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
from routers.backup_routes import router as backup_router
from routers.restore import router as restore_router
from utils.redis_client import init_stream_group
from utils.notification_consumer import consume_notifications
from model.notification import Notification
from routers.notification_router import router as notification_router
from routers.ws_router import router as ws_router
from fastapi.middleware.cors import CORSMiddleware
from routers.seatmap_router import router as seatmap_router
from routers.feedback import router as feedback_router
import logging
import traceback
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from routers.ticket_router import router as ticket_router
from utils.middleware.logger import setup_logging, LoggingMiddleware

Base.metadata.create_all(bind=engine)
logger = logging.getLogger("uvicorn.error")
setup_logging()
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

app = FastAPI()


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mydatabase")

seatlock_crud = SeatLockCRUD()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["*"],
)
@app.middleware("http")
async def global_single_middleware(request: Request, call_next):
    """
    Single middleware to:
      1) Pass through websocket upgrade requests (so websocket endpoints work)
      2) Wrap call_next in try/except to map exceptions to structured JSON responses
    """
    # allow websockets through (don't try to handle exceptions for WS upgrade)
    conn_header = request.headers.get("connection", "")
    upgrade_header = request.headers.get("upgrade", "")
    if "upgrade" in conn_header.lower() and upgrade_header.lower() == "websocket":
        return await call_next(request)

    try:
        # Normal request flow
        response = await call_next(request)
        return response

    except HTTPException as exc:
        # Reuse the status and detail that handlers in code intentionally raise.
        logger.info("HTTPException: %s %s -> %s", request.method, request.url, exc.detail)
        payload = {
            "error": "http_error",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
            "timestamp": _now_iso(),
        }
        return JSONResponse(status_code=exc.status_code, content=payload)

    except RequestValidationError as exc:
        # Pydantic/Request validation errors
        logger.debug("Validation error on %s %s: %s", request.method, request.url, exc.errors())
        payload = {
            "error": "validation_error",
            "status_code": 422,
            "detail": exc.errors(),
            "body": getattr(exc, "body", None),
            "path": str(request.url),
            "method": request.method,
            "timestamp": _now_iso(),
        }
        return JSONResponse(status_code=422, content=payload)

    except IntegrityError as exc:
        # DB integrity errors (unique constraint, FK, etc.)
        error_id = uuid.uuid4().hex
        orig_msg = ""
        try:
            orig_msg = str(exc.orig)
        except Exception:
            orig_msg = str(exc)
        # Heuristic to map unique constraint -> 409
        if "unique" in orig_msg.lower() or "duplicate" in orig_msg.lower():
            status_code = 409
            client_msg = "Duplicate value or unique constraint violated"
        else:
            status_code = 400
            client_msg = "Database integrity error"

        logger.warning("IntegrityError (%s) %s %s -> %s\nOrig: %s", error_id, request.method, request.url, client_msg, orig_msg)
        payload = {
            "error": "integrity_error",
            "status_code": status_code,
            "message": client_msg,
            "error_id": error_id,
            "path": str(request.url),
            "method": request.method,
            "timestamp": _now_iso(),
        }
        return JSONResponse(status_code=status_code, content=payload)

    except OperationalError as exc:
        # DB operational errors (connection, network, etc.) => 503
        error_id = uuid.uuid4().hex
        logger.error("OperationalError (%s) on %s %s: %s", error_id, request.method, request.url, str(exc), exc_info=exc)
        payload = {
            "error": "operational_error",
            "status_code": 503,
            "message": "Service temporarily unavailable",
            "error_id": error_id,
            "path": str(request.url),
            "method": request.method,
            "timestamp": _now_iso(),
        }
        return JSONResponse(status_code=503, content=payload)

    except Exception as exc:
        # Catch-all: log full traceback and return generic message with error_id
        error_id = uuid.uuid4().hex
        tb = traceback.format_exc()
        logger.error("Unhandled exception %s on %s %s\n%s", error_id, request.method, request.url, tb)
        payload = {
            "error": "internal_server_error",
            "status_code": 500,
            "message": "An unexpected error occurred",
            "error_id": error_id,
            "path": str(request.url),
            "method": request.method,
            "timestamp": _now_iso(),
        }
        return JSONResponse(status_code=500, content=payload)
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
        await asyncio.sleep(600)  # every 10 minutes

@app.on_event("startup")
async def startup():
    app.state.mongo_client = AsyncIOMotorClient(MONGO_URI)
    app.state.mongo_db = app.state.mongo_client[DB_NAME]
    await init_beanie(
        database=app.state.mongo_db,
        document_models=[BackupLog, RestoreLog, Notification],
    )
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
app.include_router(seatmap_router)
app.include_router(feedback_router)
app.include_router(ticket_router)
