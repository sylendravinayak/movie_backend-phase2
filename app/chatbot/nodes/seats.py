from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, not_

from database import SessionLocal
from model import BookedSeat, Seat
from model.seat import SeatLock, SeatLockStatusEnum
from crud.seat_lock_crud import SeatLockCRUD
from schemas.seat_schema import SeatLockCreate
from chatbot.state import ChatState

logger = logging.getLogger("chat_graph.seat")
logger.setLevel(logging.DEBUG)

lock_crud = SeatLockCRUD()


def _get_db() -> Session:
    return SessionLocal()


def _extract_seat_labels_from_text(text: str) -> List[str]:
    """
    Extract seat tokens like 'A5', 'B12', 'a3' from free text.
    Returns normalized upper-case labels without surrounding punctuation.
    """
    if not text:
        return []
    tokens = re.findall(r"\b[A-Za-z]\d{1,3}\b", text)
    return [t.upper() for t in tokens]


def _rows_to_id_list(rows):
    """
    Convert SQLAlchemy query rows like [(id,), (id,), ...] or objects with .seat_id
    into a flat list of ints.
    """
    ids = []
    for r in rows:
        if hasattr(r, "seat_id"):
            ids.append(r.seat_id)
        elif isinstance(r, (list, tuple)) and len(r) >= 1:
            try:
                ids.append(int(r[0]))
            except Exception:
                continue
        else:
            try:
                ids.append(int(r))
            except Exception:
                continue
    return ids


async def handle_seats_and_lock(state: ChatState) -> ChatState:
    """
    Seat handling node behaviour:
    - If seat_ids present: verify availability and create locks.
    - If seat_ids missing but seats_requested present: do NOT auto-select seats.
      Instead:
        * If user message contains seat labels, map them to seat_ids and proceed to lock.
        * Otherwise, return structured available_seats (seat_id + label) for client to pick from.
    - If seats_requested missing: prompt for number of tickets.
    - Always defensively normalize any incoming seat identifiers to numeric seat_id before DB use.
    - Respect interrupt semantics while allowing this node to run when it itself paused (next_node == 'seat')
      or when available_seats are present.
    """
    # Respect interrupt: allow this node to process when it itself paused or when available_seats exist.
    if state.get("awaiting_user"):
        if not (state.get("next_node") == "seat" or state.get("available_seats")):
            return state

    show_id = state.get("show_id")
    user_id = state.get("user_id")
    # Note: keep raw value for mapping; we'll normalize after opening DB
    raw_seat_ids = state.get("seat_ids", []) or []
    seats_requested = state.get("seats_requested")

    if not (show_id and user_id):
        state["awaiting_user"] = True
        state["response"] = "I still need show and user to lock seats."
        state["missing_fields"] = [f for f in ["show_id", "user_id"] if not state.get(f)]
        state["next_node"] = "seat"
        return state

    db = _get_db()
    try:
        now = datetime.now(timezone.utc)

        # Defensive normalization: convert any incoming seat identifiers (ints, numeric strings, labels like "A1")
        # into a list of integer seat_ids. Use available_seats mapping (if present) first, then DB lookup by seat_number.
        seat_ids: List[int] = []
        if raw_seat_ids:
            avail = state.get("available_seats") or []
            avail_map = {}
            if avail and isinstance(avail[0], dict):
                for s in avail:
                    lbl = (s.get("label") or "").strip().upper()
                    try:
                        sid = int(s.get("seat_id"))
                    except Exception:
                        continue
                    if lbl:
                        avail_map[lbl] = sid

            for entry in raw_seat_ids:
                # label string like "A1" -> try avail_map lookup first
                if isinstance(entry, str):
                    label = entry.strip().upper()
                    if label in avail_map:
                        seat_ids.append(avail_map[label])
                        continue
                    # fallback: DB lookup by seat_number & screen_id
                    try:
                        q = db.query(Seat).filter(func.lower(Seat.seat_number) == label.lower())
                        screen_id = state.get("screen_id")
                        if screen_id:
                            q = q.filter(Seat.screen_id == screen_id)
                        row = q.first()
                        if row:
                            seat_ids.append(row.seat_id)
                            continue
                    except Exception:
                        logger.debug("SEAT: DB lookup failed for label %s", entry)
                        continue
            # dedupe preserving order
            seat_ids = list(dict.fromkeys(seat_ids))

        # Update state with normalized seat_ids (so downstream code uses ints)
        if seat_ids:
            state["seat_ids"] = seat_ids
        else:
            # ensure it's an empty list (not labels)
            state["seat_ids"] = []

        # If seat_ids provided (normalized ints): validate & lock (existing behavior)
        if seat_ids:
            # 1) check already booked
            conflicts = (
                db.query(BookedSeat)
                .filter(and_(BookedSeat.show_id == show_id, BookedSeat.seat_id.in_(seat_ids)))
                .all()
            )
            if conflicts:
                state["awaiting_user"] = True
                state["response"] = "Some seats are already booked. Please choose different seats."
                state["seat_ids"] = []
                state["missing_fields"] = ["seat_ids"]
                state["next_node"] = "seat"
                return state

            # 2) check active locks
            active_locks_rows = (
                db.query(SeatLock.seat_id)
                .filter(
                    SeatLock.show_id == show_id,
                    SeatLock.seat_id.in_(seat_ids),
                    SeatLock.status == SeatLockStatusEnum.LOCKED,
                    SeatLock.expires_at > now,
                )
                .all()
            )
            active_locks = _rows_to_id_list(active_locks_rows)
            if active_locks:
                state["awaiting_user"] = True
                state["response"] = "Some seats are currently locked. Please pick other seats."
                state["seat_ids"] = []
                state["missing_fields"] = ["seat_ids"]
                state["next_node"] = "seat"
                return state

            # 3) Create locks deterministically using SeatLockCreate
            locked_ids: List[int] = []
            ttl_minutes = 10
            expires_at = now + timedelta(minutes=ttl_minutes)
            for sid in seat_ids:
                obj_in = SeatLockCreate(
                    seat_id=int(sid),
                    show_id=int(show_id),
                    user_id=int(user_id),
                    status="LOCKED",
                    locked_at=None,
                    expires_at=expires_at,
                )
                try:
                    lock_crud.create(db, obj_in=obj_in)
                except Exception as e:
                    logger.exception("Failed to create lock for seat %s (seat_ids path): %s", sid, e)
                    state["awaiting_user"] = True
                    state["response"] = "Could not lock selected seats. Please try different seats."
                    state["seat_ids"] = []
                    state["missing_fields"] = ["seat_ids"]
                    state["next_node"] = "seat"
                    return state
                locked_ids.append(sid)

            state["response"] = f"Locked seats {locked_ids} for {ttl_minutes} minutes. Shall I proceed to payment?"
            state["awaiting_user"] = False
            state["missing_fields"] = []
            state["next_node"] = None
            state.pop("available_seats", None)
            return state

        # If seats_requested missing: ask how many tickets
        if not isinstance(seats_requested, int) or seats_requested <= 0:
            state["awaiting_user"] = True
            state["response"] = "How many tickets do you need?"
            state["missing_fields"] = ["seats_requested"]
            state["next_node"] = "seat"
            return state

        # At this point: seats_requested present but seat_ids empty.
        user_msg = (state.get("message") or "").strip()
        available = state.get("available_seats") or []

        # Normalize available seats into list of dicts: {"seat_id":?, "label":?}
        structured_available: List[dict] = []
        if available:
            if isinstance(available[0], dict):
                structured_available = available
            else:
                structured_available = [{"seat_id": None, "label": str(lbl)} for lbl in available]

        # Try to map user message seat labels to seat_ids (if user replied with labels like "A1" or "A1,A2")
        selected_labels = _extract_seat_labels_from_text(user_msg)
        if selected_labels:
            labels_lower = [lbl.lower() for lbl in selected_labels]
            screen_id = state.get("screen_id")
            seat_query = db.query(Seat).filter(func.lower(Seat.seat_number).in_(labels_lower))
            if screen_id:
                seat_query = seat_query.filter(Seat.screen_id == screen_id)
            seats_found = seat_query.all()
            logger.debug("SEAT: user selected labels=%s seats_found=%s", selected_labels, [getattr(s, "seat_number", None) for s in seats_found])
            if seats_found:
                # Exclude any that are already booked or locked
                booked_rows = db.query(BookedSeat.seat_id).filter(BookedSeat.show_id == show_id).all()
                booked_ids = _rows_to_id_list(booked_rows)
                locked_rows = (
                    db.query(SeatLock.seat_id)
                    .filter(
                        SeatLock.show_id == show_id,
                        SeatLock.status == SeatLockStatusEnum.LOCKED,
                        SeatLock.expires_at > now,
                    )
                    .all()
                )
                locked_ids = _rows_to_id_list(locked_rows)

                mapped_ids = [s.seat_id for s in seats_found if s.seat_id not in booked_ids and s.seat_id not in locked_ids]
                logger.debug("SEAT: mapped_ids after excluding booked/locked = %s (booked=%s locked=%s)", mapped_ids, booked_ids, locked_ids)

                # If mapped ids count equals requested seats, accept the selection and proceed to lock
                if len(mapped_ids) == int(seats_requested):
                    # create locks using SeatLockCreate
                    locked_ids: List[int] = []
                    ttl_minutes = 10
                    expires_at = now + timedelta(minutes=ttl_minutes)
                    for sid in mapped_ids:
                        obj_in = SeatLockCreate(
                            seat_id=int(sid),
                            show_id=int(show_id),
                            user_id=int(user_id),
                            status="LOCKED",
                            locked_at=None,
                            expires_at=expires_at,
                        )
                        try:
                            lock_crud.create(db, obj_in=obj_in)
                        except Exception as e:
                            logger.exception("Failed to create lock for seat %s (label mapping path): %s", sid, e)
                            state["awaiting_user"] = True
                            state["response"] = "Could not lock selected seats. Please try different seats."
                            state["seat_ids"] = []
                            state["missing_fields"] = ["seat_ids"]
                            state["next_node"] = "seat"
                            return state
                        locked_ids.append(sid)
                    state["response"] = f"Locked seats {locked_ids} for {ttl_minutes} minutes. Shall I proceed to payment?"
                    state["awaiting_user"] = False
                    state["missing_fields"] = []
                    state["next_node"] = None
                    state.pop("available_seats", None)
                    state["seat_ids"] = mapped_ids
                    return state
                else:
                    # Some seats unavailable or count mismatch
                    state["awaiting_user"] = True
                    state["seat_ids"] = []
                    state["missing_fields"] = ["seat_ids"]
                    state["next_node"] = "seat"
                    state["response"] = (
                        "Some of the seats you selected are unavailable or the number doesn't match your requested ticket count. "
                        "Please pick available seats from the list."
                    )
                    # continue to listing branch below to refresh available seats
            # else: no seats found by label; fall through to listing available seats

        # If we reach here, either user didn't supply labels or mapping failed — list available seats
        booked_subq = db.query(BookedSeat.seat_id).filter(BookedSeat.show_id == show_id).subquery()
        locked_subq = (
            db.query(SeatLock.seat_id)
            .filter(
                SeatLock.show_id == show_id,
                SeatLock.status == SeatLockStatusEnum.LOCKED,
                SeatLock.expires_at > now,
            )
            .subquery()
        )

        seat_query = db.query(Seat).filter(Seat.is_available == True)
        screen_id = state.get("screen_id")
        if screen_id:
            seat_query = seat_query.filter(Seat.screen_id == screen_id)

        seat_query = seat_query.filter(not_(Seat.seat_id.in_(booked_subq)))
        seat_query = seat_query.filter(not_(Seat.seat_id.in_(locked_subq)))

        available_seats_rows = seat_query.order_by(Seat.seat_number.asc()).limit(200).all()
        if not available_seats_rows:
            state["awaiting_user"] = True
            state["response"] = "No seats are available right now for this show. Please try a different showtime."
            state["missing_fields"] = ["seat_ids"]
            state["next_node"] = "seat"
            return state

        seat_objs = [{"seat_id": s.seat_id, "label": s.seat_number or str(s.seat_id)} for s in available_seats_rows]
        state["available_seats"] = seat_objs
        state["seat_ids"] = []
        state["awaiting_user"] = True
        state["missing_fields"] = ["seat_ids"]
        state["next_node"] = "seat"
        examples = ", ".join([so["label"] for so in seat_objs[:20]])
        state["response"] = f"Please pick {seats_requested} seats. Examples: {examples}. Tell me the seat numbers or IDs."
        logger.debug("SEAT: presenting %d available seats", len(seat_objs))
        return state

    finally:
        db.close()