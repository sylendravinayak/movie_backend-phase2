# Updated booking_routes with robust proto import and improved gRPC error handling
import uuid
import os
import sys
import importlib.util
import types
from fastapi import APIRouter, Depends, HTTPException, status, Query
import grpc
import asyncio
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from crud.booking_crud import booking_crud
from schemas.booking_schema import BookingCreate, BookingUpdate, BookingOut as BookingResponse
from model import BookedSeat, BookedFood, Booking
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from utils.ws_manager import ws_manager
from model.seat import SeatLock
from schemas import SeatLockStatus as SeatLockStatusEnum
from sqlalchemy import and_
from datetime import datetime, timezone
from model.movie import Movie
from model.theatre import Show
from model.payments import Payment
from model.booking import BookingStatusLog, StatusChangedByEnum  # import log model and enum
from utils.redis_client import push_notification_event
import asyncio
from utils.email_servicer import EmailService
from model.user import User
from schemas import UserRole
from utils.auth.jwt_bearer import getcurrent_user,JWTBearer
from sqlalchemy.orm import joinedload

def _log_booking_status(db: Session, booking_id: int, from_status: Optional[str], to_status: str, changed_by: StatusChangedByEnum, reason: Optional[str] = None):
    # Helper: add a status log to the current transaction; caller should commit
    log = BookingStatusLog(
        booking_id=booking_id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        reason=reason
    )
    db.add(log)

def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

# Make repo root importable (works whether uvicorn run from repo root or from app/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Try to import generated proto modules. Provide robust fallbacks so imports succeed
try:
    from grpc_module.proto import payment_pb2, payment_pb2_grpc  # type: ignore
except Exception:
    try:
        from proto import payment_pb2, payment_pb2_grpc  # type: ignore
    except Exception:
        proto_dir = os.path.join(ROOT, "grpc_module", "proto")
        pb2_path = os.path.join(proto_dir, "payment_pb2.py")
        pb2_grpc_path = os.path.join(proto_dir, "payment_pb2_grpc.py")
        if not (os.path.exists(pb2_path) and os.path.exists(pb2_grpc_path)):
            raise ModuleNotFoundError(
                "Could not find generated proto modules. Expected files:\n"
                f" - {pb2_path}\n - {pb2_grpc_path}\n"
                "Run proto generation or ensure grpc_module/proto exists and is on PYTHONPATH."
            )
        if "proto" not in sys.modules:
            proto_pkg = types.ModuleType("proto")
            proto_pkg.__path__ = [proto_dir]
            sys.modules["proto"] = proto_pkg

        def _load_pkg_module(fullname: str, path: str):
            spec = importlib.util.spec_from_file_location(fullname, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module {fullname} from {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            return module

        payment_pb2 = _load_pkg_module("proto.payment_pb2", pb2_path)
        payment_pb2_grpc = _load_pkg_module("proto.payment_pb2_grpc", pb2_grpc_path)

router = APIRouter(prefix="/bookings", tags=["Bookings"])
BOOKING_PAYMENT_TARGET = os.getenv("PAYMENT_SERVICE_TARGET", "127.0.0.1:50051")

@router.get("/", response_model=List[BookingResponse])
def get_bookings(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = Query(None),
    show_id: Optional[int] = Query(None),
    current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if show_id is not None:
        filters["show_id"] = show_id
    return booking_crud.get_all(db, skip=skip, limit=limit, filters=filters)

@router.get("/{booking_id}/logs")
def get_booking_logs(booking_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    booking = booking_crud.get(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    logs = db.query(BookingStatusLog).filter(BookingStatusLog.booking_id == booking_id).order_by(BookingStatusLog.changed_at.asc()).all()
    return [
        {
            "status_log_id": l.status_log_id,
            "booking_id": l.booking_id,
            "from_status": l.from_status,
            "to_status": l.to_status,
            "changed_at": l.changed_at.isoformat() if l.changed_at else None,
            "changed_by": str(l.changed_by) if l.changed_by else None,
            "reason": l.reason,
        }
        for l in logs
    ]

@router.put("/cancel/{booking_id}")
async def delete_booking(booking_id: int, db: Session = Depends(get_db), payload: dict = Depends(JWTBearer())):
    booking = booking_crud.get(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking.booking_status).upper() == "CANCELLED":
        refund_amount = 0
        if booking.payment_id:
            payment = db.query(Payment).filter(Payment.payment_id == booking.payment_id).first()
            if payment and payment.refund_amount is not None:
                refund_amount = int(payment.refund_amount)
        return {
            "message": "Booking already cancelled",
            "booking_id": booking.booking_id,
            "refund_amount": refund_amount,
        }

    # Compute refund
    refund_amount = 0
    amount = int(booking.amount or 0)
    show = db.query(Show).filter(Show.show_id == booking.show_id).first()
    if show:
        try:
            show_dt = datetime.combine(show.show_date, show.show_time).replace(tzinfo=timezone.utc)
            now = _utcnow()
            hours_before = (show_dt - now).total_seconds() / 3600.0
            if hours_before >= 8.0:
                refund_amount = (amount * 80) // 100
        except Exception:
            refund_amount = 0

    # Update payment if present
    if booking.payment_id:
        payment = db.query(Payment).filter(Payment.payment_id == booking.payment_id).first()
        if payment:
            payment.payment_status = "REFUNDED"
            payment.refund_amount = int(refund_amount)
            db.add(payment)

    # Set booking CANCELLED and log it; commit once at end
    prev = booking.booking_status
    booking.booking_status = "CANCELLED"
    db.add(booking)
    _log_booking_status(db, booking.booking_id, prev, "CANCELLED", StatusChangedByEnum.USER, "User-initiated cancellation")
    try:
        user = db.query(User).filter(User.user_id == booking.user_id).first()
        show = db.query(Show).filter(Show.show_id == booking.show_id).first()
        movie = db.query(Movie).filter(Movie.movie_id == show.movie_id).first() if show else None

        if user and getattr(user, "email", None):
            email_service = EmailService()
            movie_title = movie.title if movie else "Your movie"
            # Format: 2025-11-03 19:30
            show_dt = None
            if show:
                show_dt = f"{show.show_date} {show.show_time.strftime('%H:%M')}"
                deeplink = f"http://localhost:3000/bookings/{booking.booking_id}"

            asyncio.create_task(
                email_service.send_booking_cancelled_email(
                    to_email=user.email,
                    user_name=user.name or "User",
                    booking_id=str(booking.booking_id),
                    cancellation_reason="user request",
                    refund_amount=float(booking.amount)*0.80,
                    deeplink=deeplink,
                )
            )
    except Exception as e:
                    # Never fail the API because email failed
        print(f"[Email] Booking confirmed email error: {type(e).__name__}: {e}")
    # Release seat locks then delete booked seats/foods
    try:
        booked_seats = db.query(BookedSeat).filter(BookedSeat.booking_id == booking.booking_id).all()
        for bs in booked_seats:
            lock = db.query(SeatLock).filter(
                SeatLock.show_id == int(booking.show_id),
                SeatLock.seat_id == int(bs.seat_id),
            ).first()
            if lock:
                lock.status = getattr(SeatLockStatusEnum, "EXPIRED", "EXPIRED")
                if hasattr(lock, "expire_at"):
                    lock.expire_at = _utcnow()
                db.add(lock)
        db.query(BookedSeat).filter(BookedSeat.booking_id == booking.booking_id).delete(synchronize_session=False)
        db.query(BookedFood).filter(BookedFood.booking_id == booking.booking_id).delete(synchronize_session=False)
    except Exception:
        pass

    db.commit()
    db.refresh(booking)
    await push_notification_event({
                "user_id": booking.user_id,
                "notification_type": "BOOKING_CANCELLED",
                "message": f"Your booking {booking.booking_reference} has been cancelled."
    })
    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking.booking_id,
        "refund_amount": int(refund_amount),
    }

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db), payload: dict = Depends(JWTBearer())):
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.seats), joinedload(Booking.foods))
        .filter(Booking.booking_id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(obj: BookingCreate, db: Session = Depends(get_db),payload: dict = Depends(JWTBearer())):
    try:
        # Create as PENDING
        booking = Booking(
            user_id=obj.user_id,
            show_id=obj.show_id,
            booking_time=obj.booking_time,
            payment_id=obj.payment_id,
            discount_id=obj.discount_id,
            booking_reference="BKNG-" + str(uuid.uuid4())[:8].upper(),
            booking_status="PENDING",
        )
        db.add(booking)
        db.flush()
        db.refresh(booking)

        # Log initial creation (None -> PENDING) and commit later with the rest
        _log_booking_status(db, booking.booking_id, None, "PENDING", StatusChangedByEnum.SYSTEM, "Booking created")

        total_amount = 0.0

        # Discount percent
        discount = (db.execute(text("SELECT discount_percent FROM discounts WHERE discount_id = :id"), {"id": obj.discount_id}).scalar_one_or_none() or 0)

        # Seats
        for seat in obj.seats:
            price = db.execute(
                text("""
                    SELECT price 
                    FROM seats s 
                    JOIN show_category_pricing scp ON scp.category_id = s.category_id 
                    WHERE scp.show_id = :show_id AND s.seat_id = :sid
                """),
                {"sid": seat, "show_id": obj.show_id},
            ).scalar_one_or_none()
            if price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(f"No price found for seat_id={seat} for show_id={obj.show_id}. "
                            "Please add a show_category_pricing entry for this show and seat category.")
                )
            total_amount += float(price)
            db.add(BookedSeat(booking_id=booking.booking_id, seat_id=seat, price=price, show_id=obj.show_id, gst_id=1))

        # Foods
        for food in obj.foods:
            unit_price = db.execute(text("SELECT price FROM food_items WHERE food_id = :fid"), {"fid": food["food_id"]}).scalar_one_or_none()
            if unit_price is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Food item with id {food['food_id']} not found.")
            category = db.execute(
                text("""
                    SELECT category_name 
                    FROM food_items fi 
                    JOIN food_categories fc ON fi.category_id = fc.category_id 
                    WHERE fi.food_id = :fid
                """),
                {"fid": food["food_id"]},
            ).scalar_one_or_none()
            if category is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category for food item id {food['food_id']} not found.")
            food_gst = db.execute(
                text("""
                    SELECT (s_gst + c_gst) FROM food_items f
                    JOIN food_categories fc ON f.category_id = fc.category_id
                    JOIN gst g ON fc.category_name = g.gst_category
                    WHERE food_id = :fid
                """),
                {"fid": food["food_id"]},
            ).scalar_one_or_none()
            if food_gst is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"GST not configured for food item id {food['food_id']}.")
            qty = int(food.get("quantity", 1))
            item_subtotal = float(unit_price) * qty
            item_gst_amount = item_subtotal * (float(food_gst) / 100.0)
            total_amount += item_subtotal + item_gst_amount
            gst_id = 2 if category == "Beverages" else 3
            db.add(BookedFood(booking_id=booking.booking_id, food_id=food["food_id"], quantity=qty, unit_price=unit_price, gst_id=gst_id))

        # Ticket GST
        ticket_gst = db.execute(text("SELECT (s_gst + c_gst) FROM gst WHERE gst_category = 'ticket'")).scalar_one_or_none()
        if ticket_gst is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket GST not configured in gst table. Add a gst entry with gst_category='ticket'.")

        total_amount = total_amount + (total_amount * float(ticket_gst) / 100.0)
        if discount:
            total_amount -= total_amount * (float(discount) / 100.0)
        booking.amount = total_amount

        # Payment
        try:
            async with grpc.aio.insecure_channel(BOOKING_PAYMENT_TARGET) as channel:
                stub = payment_pb2_grpc.PaymentServiceStub(channel)
                req = payment_pb2.CreatePaymentReq(
                    booking_id=booking.booking_id,
                    booking_reference=booking.booking_reference,
                    amount=int(booking.amount),
                    user_id=booking.user_id,
                )
                try:
                    resp = await stub.CreatePayment(req, timeout=10.0)
                except grpc.aio.AioRpcError as rpc_e:
                    code = rpc_e.code()
                    details = rpc_e.details()
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Payment RPC failed: {code.name} - {details}")

                if getattr(resp, "status", "").upper() != "SUCCESS":
                    # Payment failed -> CANCEL and log before commit
                    prev = booking.booking_status
                    booking.booking_status = "CANCELLED"
                    db.add(booking)
                    _log_booking_status(db, booking.booking_id, prev, "CANCELLED", StatusChangedByEnum.PAYMENT_SERVICE, f"Payment failed: {getattr(resp, 'message', '')}")
                    db.commit()
                    db.refresh(booking)
                    raise HTTPException(status_code=400, detail=f"Payment failed: {getattr(resp, 'message', '')}")

                # Payment succeeded -> CONFIRMED and log before commit
                prev = booking.booking_status
                booking.payment_id = resp.payment_id
                booking.booking_status = "CONFIRMED"
                db.add(booking)
                _log_booking_status(db, booking.booking_id, prev, "CONFIRMED", StatusChangedByEnum.PAYMENT_SERVICE, "Payment succeeded")
                db.commit()
                db.refresh(booking)
                try:
                    user = db.query(User).filter(User.user_id == booking.user_id).first()
                    show = db.query(Show).filter(Show.show_id == booking.show_id).first()
                    movie = db.query(Movie).filter(Movie.movie_id == show.movie_id).first() if show else None

                    if user and getattr(user, "email", None):
                        email_service = EmailService()
                        movie_title = movie.title if movie else "Your movie"
                        # Format: 2025-11-03 19:30
                        show_dt = None
                        if show:
                            show_dt = f"{show.show_date} {show.show_time.strftime('%H:%M')}"
                            deeplink = f"http://localhost:3000/bookings/{booking.booking_id}"

                        asyncio.create_task(
                            email_service.send_booking_confirmed_email(
                                to_email=user.email,
                                user_name=user.name or "User",
                                booking_id=str(booking.booking_id),
                                movie_title=movie_title,
                                show_datetime=show_dt or "",
                                total_amount=float(booking.amount or 0),
                                deeplink=deeplink,
                            )
                        )
                except Exception as e:
                    # Never fail the API because email failed
                    print(f"[Email] Booking confirmed email error: {type(e).__name__}: {e}")
                # Release seat locks
                now = _utcnow()
                for seat in obj.seats:
                    lock = db.query(SeatLock).filter(
                        SeatLock.show_id == int(booking.show_id),
                        SeatLock.seat_id == int(seat),
                        SeatLock.status == SeatLockStatusEnum.LOCKED,
                        SeatLock.expires_at > now
                    ).first()
                    if lock:
                        db.delete(lock)
                db.commit()

                await ws_manager.broadcast_to_show(str(booking.show_id), {
                    "type": "seat_booked",
                    "show_id": int(booking.show_id),
                    "seat_ids": [int(s) for s in obj.seats],
                    "booking_id": int(booking.booking_id)
                })
                await push_notification_event({
                "user_id": booking.user_id,
                "notification_type": "BOOKING_CONFIRMED",
                "message": f"Your booking {booking.booking_reference} is confirmed."
    })
                return booking

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Payment service error: {str(e)}")

    except IntegrityError as e:
        db.rollback()
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(400, "Duplicate booking. Booking reference or transaction conflict.")
        raise HTTPException(400, "Database integrity error")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create booking: {str(e)}")