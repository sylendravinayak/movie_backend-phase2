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
        # Some environments expect a top-level 'proto' package
        from proto import payment_pb2, payment_pb2_grpc  # type: ignore
    except Exception:
        # Fallback loading from files in grpc_module/proto and ensure package name 'proto'
        proto_dir = os.path.join(ROOT, "grpc_module", "proto")
        pb2_path = os.path.join(proto_dir, "payment_pb2.py")
        pb2_grpc_path = os.path.join(proto_dir, "payment_pb2_grpc.py")

        if not (os.path.exists(pb2_path) and os.path.exists(pb2_grpc_path)):
            # If proto files are missing, raise a clear error (user needs to generate protos)
            raise ModuleNotFoundError(
                "Could not find generated proto modules. Expected files:\n"
                f" - {pb2_path}\n - {pb2_grpc_path}\n"
                "Run proto generation or ensure grpc_module/proto exists and is on PYTHONPATH."
            )

        # Ensure a package module named 'proto' exists so payment_pb2_grpc's `import proto.payment_pb2` works
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

# Payment service target: prefer environment variable for local vs docker setups.
# For local runs default to localhost so Windows IPv4 connects well.
BOOKING_PAYMENT_TARGET = os.getenv("PAYMENT_SERVICE_TARGET", "127.0.0.1:50051")


@router.get("/", response_model=List[BookingResponse])
def get_bookings(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = Query(None),
    show_id: Optional[int] = Query(None),
):
    filters = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if show_id is not None:
        filters["show_id"] = show_id
    return booking_crud.get_all(db, skip=skip, limit=limit, filters=filters)


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = booking_crud.get(db, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(obj: BookingCreate, db: Session = Depends(get_db)):
    try:
        # Create booking record (PENDING until payment succeeded)
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
        db.flush()  # populate booking.booking_id
        db.refresh(booking)

        total_amount = 0.0

        # Discount percent (0 if none)
        discount = (
            db.execute(
                text("SELECT discount_percent FROM discounts WHERE discount_id = :id"),
                {"id": obj.discount_id},
            )
            .scalar_one_or_none()
            or 0
        )
        locked_seats= db.execute(
            text("SELECT seat_id FROM seat_locks where show_id = :show_id AND status = 'LOCKED'"),
            {"show_id": obj.show_id}
        ).scalars().all()



        # Seats calculation: use scalar_one_or_none and produce clear error if pricing missing
        for seat in obj.seats:
            if seat in locked_seats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seat id {seat} is locked and cannot be booked.",
                )
            price = db.execute(
                text(
                    """
                   SELECT price 
                   FROM seats s 
                   JOIN show_category_pricing scp ON scp.category_id = s.category_id 
                   WHERE scp.show_id = :show_id AND s.seat_id = :sid
                """
                ),
                {"sid": seat, "show_id": obj.show_id},
            ).scalar_one_or_none()

            if price is None:
                # Helpful error: missing show-category pricing entry
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"No price found for seat_id={seat} for show_id={obj.show_id}. "
                        "Please add a show_category_pricing entry for this show and seat category."
                    ),
                )

            total_amount += float(price)

            db.add(
                BookedSeat(
                    booking_id=booking.booking_id,
                    seat_id=seat,
                    price=price,
                    show_id=obj.show_id,
                    gst_id=1,
                )
            )

        # Food calculation: compute per-item totals and GST
        for food in obj.foods:
            unit_price = db.execute(
                text("SELECT price FROM food_items WHERE food_id = :fid"),
                {"fid": food["food_id"]},
            ).scalar_one_or_none()
            if unit_price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Food item with id {food['food_id']} not found.",
                )

            category = db.execute(
                text(
                    """
                    SELECT category_name 
                    FROM food_items fi 
                    JOIN food_categories fc ON fi.category_id = fc.category_id 
                    WHERE fi.food_id = :fid
                """
                ),
                {"fid": food["food_id"]},
            ).scalar_one_or_none()
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category for food item id {food['food_id']} not found.",
                )

            food_gst = db.execute(
                text(
                    """
                    SELECT (s_gst + c_gst) FROM food_items f
                    JOIN food_categories fc ON f.category_id = fc.category_id
                    JOIN gst g ON fc.category_name = g.gst_category
                    WHERE food_id = :fid
                """
                ),
                {"fid": food["food_id"]},
            ).scalar_one_or_none()
            if food_gst is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GST not configured for food item id {food['food_id']}.",
                )

            qty = int(food.get("quantity", 1))
            item_subtotal = float(unit_price) * qty
            item_gst_amount = item_subtotal * (float(food_gst) / 100.0)
            item_total = item_subtotal + item_gst_amount

            total_amount += item_total

            gst_id = 2 if category == "Beverages" else 3

            db.add(
                BookedFood(
                    booking_id=booking.booking_id,
                    food_id=food["food_id"],
                    quantity=qty,
                    unit_price=unit_price,
                    gst_id=gst_id,
                )
            )

        # Ticket GST lookup: be tolerant and give actionable error if missing
        ticket_gst = db.execute(
            text("SELECT (s_gst + c_gst) FROM gst WHERE gst_category = 'ticket'")
        ).scalar_one_or_none()
        if ticket_gst is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket GST not configured in gst table. Add a gst entry with gst_category='ticket'.",
            )

        total_amount = total_amount + (total_amount * float(ticket_gst) / 100.0)

        # Apply discount
        if discount:
            total_amount -= total_amount * (float(discount) / 100.0)

        booking.amount = total_amount

        # Call payment gRPC service using grpc.aio and call the RPC directly (stub.CreatePayment)
        try:
            async with grpc.aio.insecure_channel(BOOKING_PAYMENT_TARGET) as channel:
                # Attempt RPC directly with timeout; this will raise AioRpcError if unavailable
                stub = payment_pb2_grpc.PaymentServiceStub(channel)

                req = payment_pb2.CreatePaymentReq(
                    booking_id=booking.booking_id,
                    booking_reference=booking.booking_reference,
                    amount=int(booking.amount),
                    user_id=booking.user_id,
                )

                try:
                    # rpc-level timeout to avoid indefinite hang
                    resp = await stub.CreatePayment(req, timeout=10.0)
                except grpc.aio.AioRpcError as rpc_e:
                    # Common codes: UNAVAILABLE (server not reachable), DEADLINE_EXCEEDED, etc.
                    code = rpc_e.code()
                    details = rpc_e.details()
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Payment RPC failed: {code.name} - {details}",
                    )

                if getattr(resp, "status", "").upper() != "SUCCESS":
                    booking.booking_status = "CANCELLED"
                    db.add(booking)
                    db.commit()
                    db.refresh(booking)
                    raise HTTPException(status_code=400, detail=f"Payment failed: {resp.message}")

                # Payment succeeded -> finalize booking
                booking.payment_id = resp.payment_id
                booking.booking_status = "CONFIRMED"
                db.add(booking)
                db.commit()
                db.refresh(booking)
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
                return booking
                

        except HTTPException:
            # re-raise mapped HTTPExceptions
            raise
        except Exception as e:
            # catch-all for payment communication issues
            raise HTTPException(status_code=502, detail=f"Payment service error: {str(e)}")

    except IntegrityError as e:
        db.rollback()
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(400, "Duplicate booking. Booking reference or transaction conflict.")
        raise HTTPException(400, "Database integrity error")
    except HTTPException:
        # re-raise mapped HTTPExceptions
        raise
    except Exception as e:
        db.rollback()
        # Provide the original exception message to aid debugging
        raise HTTPException(500, f"Failed to create booking: {str(e)}")


@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(booking_id: int, obj: BookingUpdate, db: Session = Depends(get_db)):
    booking = booking_crud.get(db, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking_crud.update(db, booking, obj)


@router.delete("/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    return booking_crud.remove(db, booking_id)