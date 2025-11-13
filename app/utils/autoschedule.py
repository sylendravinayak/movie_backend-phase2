from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from database import get_db
from utils.auth.jwt_bearer import getcurrent_user
from model.movie import Movie
from model.theatre import Screen, Show
from model.user import User
from schemas import UserRole

router = APIRouter()

# ===================== Pydantic Models =====================

class MovieQuota(BaseModel):
    movie_id: int
    min_shows_per_day: int = Field(ge=0)
    max_shows_per_day: Optional[int] = Field(default=None, ge=0)

    @validator("max_shows_per_day")
    def validate_max(cls, v, values):
        if v is not None and "min_shows_per_day" in values and v < values["min_shows_per_day"]:
            raise ValueError("max_shows_per_day cannot be less than min_shows_per_day")
        return v

class ScreenAssignment(BaseModel):
    screen_id: int
    movies: List[MovieQuota]

class HybridScheduleRequest(BaseModel):
    start_date: date
    days: int = Field(gt=0, le=31)
    buffer_minutes: int = Field(gt=0, le=60)
    default_open_time: time
    default_close_time: time
    per_screen_assignments: List[ScreenAssignment]
    dry_run: bool = False

    @validator("default_close_time")
    def validate_times(cls, v, values):
        if "default_open_time" in values and v <= values["default_open_time"]:
            raise ValueError("default_close_time must be after default_open_time")
        return v

class ScheduledShow(BaseModel):
    date: date
    start: str
    end: str
    movie_id: int
    screen_id: int

class WarningEntry(BaseModel):
    code: str
    message: str
    context: Dict[str, Any] = {}

class HybridScheduleResponse(BaseModel):
    message: str
    schedule: List[ScheduledShow]
    warnings: List[WarningEntry]


# ===================== Utilities =====================

def minutes_between(start_t: time, end_t: time) -> int:
    dt_start = datetime.combine(date.today(), start_t)
    dt_end = datetime.combine(date.today(), end_t)
    return max(0, int((dt_end - dt_start).total_seconds() // 60))

def add_minutes(base: time, minutes: int) -> time:
    dt = datetime.combine(date.today(), base) + timedelta(minutes=minutes)
    return dt.time()

def show_exists(db: Session, screen_id: int, show_date: date, start_time: time) -> bool:
    return db.query(Show).filter(
        Show.screen_id == screen_id,
        Show.show_date == show_date,
        Show.show_time == start_time
    ).first() is not None


# ===================== Free Window Construction =====================

def build_free_windows(
    open_time: time,
    close_time: time,
    existing: List[Tuple[time, time]],
    buffer: int
) -> List[Tuple[time, time]]:
    """
    Build non-overlapping free windows between existing shows.
    existing: list of (start_time, end_time) for already scheduled shows (sorted).
    Buffer is respected by shrinking windows so new shows never violate turnaround
    relative to existing shows.
    """
    windows: List[Tuple[time, time]] = []
    # Ensure sorted
    existing_sorted = sorted(existing, key=lambda x: x[0])

    current_start = open_time
    for (s, e) in existing_sorted:
        # Window ends buffer minutes before existing show starts
        window_end_candidate = add_minutes(s, -buffer) if buffer > 0 else s
        if window_end_candidate > current_start:
            windows.append((current_start, window_end_candidate))
        # Next window starts buffer minutes after existing show ends
        next_start = add_minutes(e, buffer) if buffer > 0 else e
        if next_start > current_start:
            current_start = next_start

    if current_start < close_time:
        windows.append((current_start, close_time))

    # Filter out invalid (negative or zero length) windows
    filtered = [(ws, we) for (ws, we) in windows if ws < we]
    return filtered



def greedy_day_schedule_with_windows(
    day: date,
    screen: Screen,
    quotas: List[MovieQuota],
    movies_lookup: Dict[int, Movie],
    buffer: int,
    filler_pool: List[int],
    warnings: List[WarningEntry],
    open_default: time,
    close_default: time,
    existing_shows: List[Show]
) -> List[Dict[str, Any]]:
    """
    Schedules quota & filler movies inside free windows derived from existing shows.
    existing_shows: persisted shows already on this screen/day (immutable).
    """
    open_time: time = getattr(screen, "open_time", None) or open_default
    close_time: time = getattr(screen, "close_time", None) or close_default

    if open_time >= close_time:
        warnings.append(WarningEntry(
            code="INVALID_WINDOW",
            message=f"Screen {screen.screen_id} has invalid times; skipping day.",
            context={"day": str(day)}
        ))
        return []

    # Collect existing intervals
    existing_intervals: List[Tuple[time, time]] = [(show.show_time, show.end_time) for show in existing_shows]
    free_windows = build_free_windows(open_time, close_time, existing_intervals, buffer)

    if not free_windows:
        warnings.append(WarningEntry(
            code="NO_FREE_WINDOWS",
            message="All time is occupied by existing shows.",
            context={"screen_id": screen.screen_id, "day": str(day)}
        ))
        return []

    # Validate and prepare quotas
    prepared = []
    for q in quotas:
        movie = movies_lookup.get(q.movie_id)
        if not movie:
            warnings.append(WarningEntry(
                code="MISSING_MOVIE",
                message=f"Movie {q.movie_id} not found; quota ignored.",
                context={"screen_id": screen.screen_id, "day": str(day)}
            ))
            continue
        duration = movie.duration or 0
        if duration <= 0:
            warnings.append(WarningEntry(
                code="INVALID_DURATION",
                message=f"Movie {q.movie_id} has non-positive duration; quota ignored.",
                context={"screen_id": screen.screen_id}
            ))
            continue
        prepared.append({
            "movie_id": q.movie_id,
            "min": q.min_shows_per_day,
            "max": q.max_shows_per_day if q.max_shows_per_day is not None else float("inf"),
            "duration": duration,
            "scheduled": 0
        })

    # Sort quotas by descending duration to reduce fragmentation (heuristic)
    prepared.sort(key=lambda x: x["duration"], reverse=True)

    # Filler candidates (include zero-min quota movies + global filler pool)
    filler_candidates = list({*filler_pool, *[p["movie_id"] for p in prepared if p["min"] == 0]})
    filler_candidates = [
        m for m in filler_candidates
        if movies_lookup.get(m) and (movies_lookup[m].duration or 0) > 0
    ]
    # Sort fillers ascending to utilize space efficiently
    filler_candidates.sort(key=lambda mid: movies_lookup[mid].duration or 0)

    def can_place_quota_entry(entry) -> bool:
        return entry["scheduled"] < entry["max"]

    def still_unmet_min(entry) -> bool:
        return entry["scheduled"] < entry["min"]

    schedule: List[Dict[str, Any]] = []

    # Iterate over each free window independently
    for (w_start, w_end) in free_windows:
        current_time = w_start

        def fits(movie_id: int, now: time, window_end: time) -> bool:
            movie = movies_lookup[movie_id]
            dur = movie.duration or 0
            if dur <= 0:
                return False
            # We only add buffer after show if we have remaining time for another show; but for fit check:
            remaining = minutes_between(now, window_end)
            # If the show ends exactly at window_end we allow (no buffer after final show)
            return dur <= remaining

        # PHASE 1: Place unmet min quotas first (round-robin over prepared list)
        while any(still_unmet_min(e) for e in prepared):
            placed = False
            for entry in prepared:
                if not still_unmet_min(entry):
                    continue
                if not can_place_quota_entry(entry):
                    continue
                if not fits(entry["movie_id"], current_time, w_end):
                    continue
                movie = movies_lookup[entry["movie_id"]]
                start_t = current_time
                end_t = add_minutes(start_t, movie.duration)
                schedule.append({
                    "date": day,
                    "start": start_t.strftime("%H:%M"),
                    "end": end_t.strftime("%H:%M"),
                    "movie_id": entry["movie_id"],
                    "screen_id": screen.screen_id,
                })
                entry["scheduled"] += 1
                # Compute next potential time with buffer; only advance if room remains
                next_time = add_minutes(end_t, buffer)
                # If next_time overshoots window, we end the window usage
                if next_time > w_end:
                    current_time = end_t  # final show flush with end
                    placed = True
                    break
                current_time = next_time
                placed = True
            if not placed:
                # Cannot fit remaining min quotas in this window; move to next window
                break

        # If time left, PHASE 2: Additional quota up to max, else fillers
        safety = 0
        while current_time < w_end and safety < 500:
            safety += 1
            remaining_minutes = minutes_between(current_time, w_end)

            # Try additional quota movies first (those below max)
            quota_candidate = next(
                (e for e in prepared
                 if can_place_quota_entry(e) and fits(e["movie_id"], current_time, w_end)),
                None
            )
            if quota_candidate:
                movie = movies_lookup[quota_candidate["movie_id"]]
                start_t = current_time
                end_t = add_minutes(start_t, movie.duration)
                schedule.append({
                    "date": day,
                    "start": start_t.strftime("%H:%M"),
                    "end": end_t.strftime("%H:%M"),
                    "movie_id": quota_candidate["movie_id"],
                    "screen_id": screen.screen_id,
                })
                quota_candidate["scheduled"] += 1
                next_time = add_minutes(end_t, buffer)
                current_time = end_t if next_time > w_end else next_time
                continue

            # Filler attempt
            filler_candidate = next(
                (m for m in filler_candidates if fits(m, current_time, w_end)),
                None
            )
            if filler_candidate is None:
                # Gap remains but no movie fits
                leftover = minutes_between(current_time, w_end)
                if leftover > 0:
                    warnings.append(WarningEntry(
                        code="LEFTOVER_GAP",
                        message="Unfilled gap in window; no movie fits.",
                        context={
                            "screen_id": screen.screen_id,
                            "day": str(day),
                            "gap_minutes": leftover,
                            "window_start": w_start.strftime("%H:%M"),
                            "window_end": w_end.strftime("%H:%M")
                        }
                    ))
                break
            movie = movies_lookup[filler_candidate]
            start_t = current_time
            end_t = add_minutes(start_t, movie.duration)
            schedule.append({
                "date": day,
                "start": start_t.strftime("%H:%M"),
                "end": end_t.strftime("%H:%M"),
                "movie_id": filler_candidate,
                "screen_id": screen.screen_id,
            })
            next_time = add_minutes(end_t, buffer)
            current_time = end_t if next_time > w_end else next_time
        if safety >= 500:
            warnings.append(WarningEntry(
                code="WINDOW_SAFETY_ABORT",
                message="Aborted scheduling inside window due to safety iteration cap.",
                context={"screen_id": screen.screen_id, "day": str(day),
                         "window_start": w_start.strftime("%H:%M"),
                         "window_end": w_end.strftime("%H:%M")}
            ))

    # Final unmet quota warnings
    for entry in prepared:
        if entry["scheduled"] < entry["min"]:
            warnings.append(WarningEntry(
                code="UNMET_MIN_QUOTA",
                message=f"Movie {entry['movie_id']} unmet minimum quota.",
                context={
                    "screen_id": screen.screen_id,
                    "day": str(day),
                    "scheduled": entry["scheduled"],
                    "min": entry["min"]
                }
            ))
        if entry["scheduled"] > entry["max"]:
            warnings.append(WarningEntry(
                code="EXCEEDED_MAX_QUOTA",
                message=f"Movie {entry['movie_id']} exceeded max quota.",
                context={
                    "screen_id": screen.screen_id,
                    "day": str(day),
                    "scheduled": entry["scheduled"],
                    "max": entry["max"]
                }
            ))

    return schedule


# ===================== Persistence =====================

def persist_schedule(db: Session, rows: List[Dict[str, Any]], warnings: List[WarningEntry]) -> None:
    for item in rows:
        try:
            show_date: date = item["date"]
            start_t = datetime.strptime(item["start"], "%H:%M").time()
            end_t = datetime.strptime(item["end"], "%H:%M").time()
        except Exception as e:
            warnings.append(WarningEntry(
                code="PARSE_ERROR",
                message="Malformed schedule entry skipped.",
                context={"entry": str(item), "error": str(e)}
            ))
            continue
        if show_exists(db, item["screen_id"], show_date, start_t):
            warnings.append(WarningEntry(
                code="DUPLICATE_SHOW",
                message="Show already exists; skipped.",
                context={"screen_id": item["screen_id"], "date": str(show_date), "start": item["start"]}
            ))
            continue
        db.add(Show(
            movie_id=int(item["movie_id"]),
            screen_id=int(item["screen_id"]),
            show_date=show_date,
            show_time=start_t,
            end_time=end_t,
        ))


