from datetime import datetime, date, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from model import Show, Screen, Movie, Booking, BookedSeat, BookedFood
from model.theatre import ShowStatusEnum
from utils.slotfinder import find_available_slots
from schemas.theatre_schema import ShowCreate, ShowUpdate, ShowOut
from crud.show_crud import show_crud
from utils.autoschedule import generate_week_schedule
from schemas import UserRole
router = APIRouter(prefix="/shows", tags=["Shows"])
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
# -----------------------------
# CREATE SHOW
# -----------------------------
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

@router.post("/", response_model=ShowOut, status_code=status.HTTP_201_CREATED)
def create_show(show_in: ShowCreate, db: Session = Depends(get_db)):
    # 1) Fetch movie duration
    movie = db.query(Movie).filter(Movie.movie_id == show_in.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # 2) Compute end_time from start + duration
    start_dt = datetime.combine(show_in.show_date, show_in.show_time)
    end_dt = start_dt + timedelta(minutes=int(movie.duration))
    computed_end_time = end_dt.time()

    # 3) Overlap check: same screen and date, (existing.start < new.end) AND (existing.end > new.start)
    overlap = (
        db.query(Show)
        .filter(
            Show.screen_id == show_in.screen_id,
            Show.show_date == show_in.show_date,
            Show.show_time < computed_end_time,
            Show.end_time > show_in.show_time,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Overlapping show exists for this screen and date",
        )

    # 4) Create the show without mutating show_in
    show = Show(
        movie_id=show_in.movie_id,
        screen_id=show_in.screen_id,
        show_date=show_in.show_date,
        show_time=show_in.show_time,
        end_time=computed_end_time,
        status=show_in.status,
    )
    db.add(show)
    db.commit()
    db.refresh(show)
    return show

# -----------------------------
# GET ALL SHOWS (with filters)
# -----------------------------
@router.get("/", response_model=List[ShowOut])
def get_all_shows(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    movie_id: Optional[int] = None,
    screen_id: Optional[int] = None,
    status: Optional[str] = None,
    show_date: Optional[str] = Query(None, description="Filter by show date (YYYY-MM-DD)"),
    payload: dict = Depends(JWTBearer())
):
    filters = {}
    if movie_id:
        filters["movie_id"] = movie_id
    if screen_id:
        filters["screen_id"] = screen_id
    if status:
        filters["status"] = status
    if show_date:
        filters["show_date"] = show_date

    return show_crud.get_all(db=db, skip=skip, limit=limit, filters=filters)

# -----------------------------
# CANCEL A SHOW + CANCEL ALL ITS BOOKINGS
# -----------------------------
@router.put("/{show_id}/cancel", response_model=ShowOut)
def cancel_show(show_id: int, db: Session = Depends(get_db), current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))):
    show = show_crud.get(db=db, id=show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # If already cancelled, still ensure bookings and their items are cleaned up
    already_cancelled = str(show.status) == ShowStatusEnum.CANCELLED.value

    # 1) Mark show as CANCELLED (idempotent)
    show.status = ShowStatusEnum.CANCELLED.value
    db.add(show)

    # 2) Cancel all bookings for this show (idempotent)
    db.query(Booking).filter(Booking.show_id == show_id).update(
        {Booking.booking_status: "CANCELLED"},
        synchronize_session=False
    )

    # 3) Delete all booked seats and foods for those bookings
    #    Use booking_ids list to avoid DB engine incompatibilities with subquery IN deletes.
    booking_ids = [b.booking_id for b in db.query(Booking).with_entities(Booking.booking_id).filter(Booking.show_id == show_id).all()]
    if booking_ids:
        db.query(BookedSeat).filter(BookedSeat.booking_id.in_(booking_ids)).delete(synchronize_session=False)
        db.query(BookedFood).filter(BookedFood.booking_id.in_(booking_ids)).delete(synchronize_session=False)

    db.commit()
    db.refresh(show)

    return show

@router.post("/auto-schedule")
def auto_schedule(
    start_date: datetime = Query(..., description="Start date for scheduling (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    movies = db.query(Movie).filter(Movie.is_active == True).all()
    screens = db.query(Screen).all()

    if not movies or not screens:
        raise HTTPException(status_code=400, detail="No movies or screens available")

    movie_list = [{"id": m.movie_id, "duration": m.duration} for m in movies]
    screen_list = [{"id": s.screen_id} for s in screens]

    schedule = generate_week_schedule(
        movie_list,
        screen_list,
        start_date.date(),
        time(9, 0),
        time(23, 59),
        buffer=60
    )

    # Optionally save schedule into DB
    for s in schedule:
        show = Show(
            movie_id=s["movie_id"],
            screen_id=s["screen_id"],
            show_date=datetime.strptime(s["date"], "%Y-%m-%d").date(),
            show_time=datetime.strptime(s["start"], "%H:%M").time(),
            end_time=datetime.strptime(s["end"], "%H:%M").time()
        )
        db.add(show)
    db.commit()

    return {"message": "Weekly schedule generated successfully", "schedule": schedule}

@router.get("/available-slots")
def get_available_slots(
    screen_id: int,
    movie_id: int,
    date: datetime = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(getcurrent_user(UserRole.ADMIN.value))
):
    # 1) Validate screen
    screen = db.query(Screen).filter(Screen.screen_id == screen_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # 2) Get movie duration
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie_duration = movie.duration  # must be in your Movie model

    # 3) Fetch existing shows for that screen/date
    shows = (
        db.query(Show)
        .filter(Show.screen_id == screen_id, Show.show_date == date.date())
        .order_by(Show.show_time)
        .all()
    )

    if not shows:
        # if no shows, entire day is open
        return {
            "available_slots": [
                {"start": "09:00", "end": "23:59"}  # or theatre operational hours
            ]
        }

    # 4) Convert to (start, end) tuples
    existing_shows = []
    for s in shows:
        end_time = (
            datetime.combine(datetime.today(), s.show_time)
            + timedelta(minutes=movie_duration + 15)
        ).time()
        existing_shows.append((s.show_time, end_time))

    # 5) Find available slots
    available = find_available_slots(
        existing_shows,
        movie_duration,
        time(9, 0),    # theatre start
        time(23, 59),  # theatre close
        buffer=60
    )

    # 6) Format output
    slots = [{"start": str(s), "end": str(e)} for s, e in available]
    return {"available_slots": slots}

# -----------------------------
# GET SHOW BY ID
# -----------------------------
@router.get("/{show_id}", response_model=ShowOut,)
def get_show(show_id: int, db: Session = Depends(get_db), current_user: dict = Depends(JWTBearer())):
    show = show_crud.get(db=db, id=show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show

# -----------------------------
# UPDATE SHOW
# -----------------------------
#@router.put("/{show_id}", response_model=ShowOut)
def update_show(show_id: int, show_in: ShowUpdate, db: Session = Depends(get_db)):
    db_obj = show_crud.get(db=db, id=show_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Show not found")
    return show_crud.update(db=db, db_obj=db_obj, obj_in=show_in)

# -----------------------------
# DELETE SHOW
# -----------------------------
#@router.delete("/{show_id}")
def delete_show(show_id: int, db: Session = Depends(get_db)):
    return show_crud.remove(db=db, id=show_id)