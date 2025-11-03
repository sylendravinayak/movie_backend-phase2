from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
from database import get_db

router = APIRouter(tags=["Seatmap UI"])

templates = Jinja2Templates(directory="templates")

@router.get("/seatmap/{show_id}")
def render_seatmap(request: Request, show_id: int, user_id: int, db: Session = Depends(get_db)):
    # 1) resolve screen for the show
    screen_id = db.execute(
        text("SELECT screen_id FROM shows WHERE show_id = :sid"),
        {"sid": show_id},
    ).scalar_one_or_none()
    if screen_id is None:
        raise HTTPException(status_code=404, detail="Show not found")

    # 2) seat + category + price for this show
    seat_rows = db.execute(
        text("""
            SELECT s.seat_id, s.seat_number, s.row_number, s.col_number, s.category_id,
                   COALESCE(fc.category_name, 'Uncategorized') AS category_name,
                   scp.price
            FROM seats s
            LEFT JOIN seat_categories fc ON s.category_id = fc.category_id
            LEFT JOIN show_category_pricing scp
                   ON scp.category_id = s.category_id AND scp.show_id = :sid
            WHERE s.screen_id = :screen
            ORDER BY s.category_id NULLS LAST, s.row_number, s.col_number, s.seat_id
        """),
        {"sid": show_id, "screen": screen_id},
    ).mappings().all()

    # 3) category pricing list for header rendering
    categories = db.execute(
        text("""
            SELECT scp.category_id, fc.category_name, scp.price
            FROM show_category_pricing scp
            JOIN seat_categories fc ON fc.category_id = scp.category_id
            WHERE scp.show_id = :sid
            ORDER BY scp.category_id
        """),
        {"sid": show_id},
    ).mappings().all()

    # 4) booked and locked seats
    booked_ids = db.execute(
        text("SELECT seat_id FROM booked_seats WHERE show_id = :sid"),
        {"sid": show_id},
    ).scalars().all()

    locks = db.execute(
        text("""
            SELECT seat_id, user_id, expires_at
            FROM seat_locks
            WHERE show_id = :sid
              AND status = 'LOCKED'
              AND expires_at > NOW()
        """),
        {"sid": show_id},
    ).mappings().all()

    # build a normalized seat payload
    seats = [
        {
            "seat_id": int(r["seat_id"]),
            "seat_number": r["seat_number"],
            "row_number": int(r["row_number"]),
            "col_number": int(r["col_number"]),
            "category_id": None if r["category_id"] is None else int(r["category_id"]),
            "category_name": r["category_name"],
            "price": float(r["price"]) if r["price"] is not None else 0.0,
        }
        for r in seat_rows
    ]

    ctx: dict[str, Any] = {
        "request": request,
        "show_id": int(show_id),
        "user_id": int(user_id),
        "seats": seats,
        "categories": [
            {
                "category_id": int(c["category_id"]),
                "category_name": c["category_name"],
                "price": float(c["price"]),
            }
            for c in categories
        ],
        "booked_ids": [int(s) for s in booked_ids],
        "locks": [
            {"seat_id": int(l["seat_id"]), "user_id": int(l["user_id"])} for l in locks
        ],
    }
    return templates.TemplateResponse("seatmap.html", ctx)