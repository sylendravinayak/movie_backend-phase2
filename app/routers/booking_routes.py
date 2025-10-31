import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
import grpc
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from crud.booking_crud import booking_crud
from schemas.booking_schema import BookingCreate, BookingUpdate,BookingOut as BookingResponse
from model import BookedSeat, BookedFood, Booking
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError


router = APIRouter(prefix="/bookings", tags=["Bookings"])
def get_grpc_channel():
    # simple helper — you can pool channels
    return grpc.aio.insecure_channel("payment-service:50051")

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
        # 1️⃣ Create booking first
        booking = Booking(
            user_id=obj.user_id,
            show_id=obj.show_id,
            booking_time=obj.booking_time,
            payment_id=obj.payment_id,
            discount_id=obj.discount_id,
            booking_reference = "BKNG-" + str(uuid.uuid4())[:8].upper()
        )

        db.add(booking)
        db.flush()
        # db.commit()         # required to persist booking_id
        db.refresh(booking)


        total_amount = 0

        # 2️⃣ Apply discount if exists
        discount = db.execute(
            text("SELECT discount_percent FROM discounts WHERE discount_id = :id"),
            {"id": obj.discount_id}
        ).scalar_one_or_none() or 0
        print("Discount Percent:", discount)
        # 3️⃣ Seats calculation
        for seat in obj.seats:
            price = db.execute(
                text("""
                   SELECT price 
                   FROM seats s 
                   JOIN show_category_pricing scp ON scp.category_id = s.category_id 
                   WHERE scp.show_id = :show_id AND s.seat_id = :sid
                """),
                {"sid": seat, "show_id": obj.show_id}
            ).scalar_one()

            total_amount += float(price)
            print("Seat Price:", total_amount)

            db.add(BookedSeat(
                booking_id=booking.booking_id,
                seat_id=seat,
                price=price,
                show_id=obj.show_id,
                gst_id=1
            ))

        # 4️⃣ Food calculation
        food_amount = 0
        for food in obj.foods:
            unit_price = db.execute(
                text("SELECT price FROM food_items WHERE food_id = :fid"),
                {"fid": food["food_id"]}
            ).scalar_one()

            category = db.execute(
                text("""
                    SELECT category_name 
                    FROM food_items fi 
                    JOIN food_categories fc ON fi.category_id = fc.category_id 
                    WHERE fi.food_id = :fid
                """),
                {"fid": food["food_id"]}
            ).scalar_one()

            food_gst = db.execute(
                text("""
                    select s_gst+c_gst from food_items f join food_categories fc on f.category_id =fc.category_id join gst g on fc.category_name = gst_category where food_id=:fid;
                """),
                {"fid": food["food_id"]}
            ).scalar_one()

            food_amount += float(unit_price) * food["quantity"]
            food_amount += food_amount * food_gst / 100
            total_amount += food_amount
        
            gst_id = 2 if category == "Beverages" else 3

            db.add(BookedFood(
                booking_id=booking.booking_id,
                food_id=food["food_id"],
                quantity=food["quantity"],
                unit_price=unit_price,
                gst_id=gst_id
            ))

        # 5️⃣ GST lookup (fixed your SQL)
        ticket_gst = db.execute(
            text("SELECT (s_gst + c_gst) FROM gst WHERE gst_category = 'ticket'")
        ).scalar_one()

        print("Ticket GST:", ticket_gst)
        
        total_gst = ticket_gst 
        total_amount = total_amount + (total_amount * total_gst / 100)

        if discount:
            total_amount -= (total_amount * discount / 100)
        booking.amount = total_amount
        # Ensure channel is started
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except IntegrityError as e:
        db.rollback()
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(400, "Duplicate booking. Booking reference already exists.")
        raise HTTPException(400, "Database integrity error")
    except Exception as e:
        db.rollback()
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
