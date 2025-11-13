from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, true
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from model.booking import Booking
from model.theatre import Show, Screen
from model.movie import Movie
from model.user import User


router = APIRouter(prefix="/reports", tags=["reports"])

# ---------- Schemas ----------

class DailySalesItem(BaseModel):
    date: date
    revenue: float
    bookings: int

class ShowOccupancyItem(BaseModel):
    show_id: int
    show_time: datetime
    movie_title: Optional[str]
    screen: Optional[str]
    seats_sold: int
    capacity: int
    occupancy_pct: float

class UserStats(BaseModel):
    total_users: int
    new_users: int
    active_users: int
    retention_pct: float

# ---------- Helpers ----------

def parse_date(d: Optional[date], default_delta_days: int) -> date:
    return d or (date.today() - timedelta(days=default_delta_days))

# ---------- Endpoints ----------

@router.get(
    "/daily-sales",
    response_model=List[DailySalesItem],
    summary="Revenue per day",
    description="Aggregated booking revenue per day for a given date range.",
)
async def daily_sales(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    start = parse_date(start_date, 7)
    end = end_date or date.today()

    stmt = (
        select(
            func.date_trunc("day", Booking.booking_date).label("day"),
            func.sum(Booking.amount).label("revenue"),
            func.count(func.distinct(Booking.booking_id)).label("bookings"),
        )
        .where(
            and_(
                Booking.booking_date >= datetime.combine(start, datetime.min.time()),
                Booking.booking_date <= datetime.combine(end, datetime.max.time()),
            )
        )
        .group_by("day")
        .order_by("day")
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        DailySalesItem(
            date=row.day.date(),
            revenue=float(row.revenue or 0),
            bookings=int(row.bookings or 0),
        )
        for row in rows
    ]


@router.get(
    "/show-occupancy",
    response_model=List[ShowOccupancyItem],
    summary="Show occupancy stats",
    description="Seats sold, capacity, and occupancy percentage for shows.",
)
async def show_occupancy(
    date_filter: Optional[date] = Query(None, description="Filter shows by calendar date"),
    movie_id: Optional[int] = Query(None),
    screen_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # Build conditions
    conditions = []
    if date_filter:
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = datetime.combine(date_filter, datetime.max.time())
        conditions.append(and_(Show.show_time >= start_dt, Show.show_time <= end_dt))
    if movie_id:
        conditions.append(Show.movie_id == movie_id)
    if screen_id:
        conditions.append(Show.screen_id == screen_id)

    # Select show info + seats sold (count of bookings), capacity and screen screen_name
    stmt = (
        select(
            Show.show_id.label("show_id"),
            Show.show_time,
            Movie.title.label("movie_title"),
            func.coalesce(func.count(Booking.booking_id), 0).label("seats_sold"),
            Screen.screen_name.label("screen"),
        )
        .select_from(Show)
        .join(Movie, Movie.movie_id == Show.movie_id, isouter=True)
        .join(Screen, Screen.screen_id == Show.screen_id, isouter=True)
        .join(Booking, Booking.show_id == Show.show_id, isouter=True)
        .where(and_(*conditions) if conditions else true())
        .group_by(Show.show_id, Show.show_time, Movie.title,  Screen.screen_name)
        .order_by(Show.show_time)
    )

    result = db.execute(stmt)
    rows = result.all()

    output: List[ShowOccupancyItem] = []
    for row in rows:
       
        
        output.append(
            ShowOccupancyItem(
                show_id=row.show_id,
                show_time=row.show_time,
                movie_title=row.movie_title,
                screen=row.screen,
                
             
            )
        )
    return output


@router.get(
    "/user-stats",
    response_model=UserStats,
    summary="User registration & active user stats",
    description="Overall totals plus new and active users for a date range.",
)
async def user_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    start = parse_date(start_date, 30)
    end = end_date or date.today()
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    total_users_stmt = select(func.count(User.id))
    # NOTE: Adjust 'User.created_at' to your actual user registration timestamp column.
    new_users_stmt = select(func.count(User.id)).where(
        and_(User.created_at >= start_dt, User.created_at <= end_dt)
    )
    active_users_stmt = (
        select(func.count(func.distinct(Booking.user_id)))
        .where(and_(Booking.booking_date >= start_dt, Booking.booking_date <= end_dt))
    )

    total_users = (await db.execute(total_users_stmt)).scalar_one()
    new_users = (await db.execute(new_users_stmt)).scalar_one()
    active_users = (await db.execute(active_users_stmt)).scalar_one()

    retention_pct = round((active_users / total_users) * 100, 2) if total_users else 0.0

    return UserStats(
        total_users=int(total_users or 0),
        new_users=int(new_users or 0),
        active_users=int(active_users or 0),
        retention_pct=retention_pct,
    )