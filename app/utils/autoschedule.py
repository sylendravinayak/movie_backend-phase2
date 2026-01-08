from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy. orm import Session

from database import get_db
from utils.auth. jwt_bearer import getcurrent_user
from model.movie import Movie
from model.theatre import Screen, Show
from schemas.theatre_schema import ShowStatus
from model.user import User
from schemas import UserRole

router = APIRouter()

# ===================== Pydantic Models =====================

class MovieQuota(BaseModel):
    movie_id: int
    min_shows_per_day: int = Field(ge=0)
    max_shows_per_day:  Optional[int] = Field(default=None, ge=0)

    @validator("max_shows_per_day")
    def validate_max(cls, v, values):
        if v is not None and "min_shows_per_day" in values and v < values["min_shows_per_day"]: 
            raise ValueError("max_shows_per_day cannot be less than min_shows_per_day")
        return v

class ScreenAssignment(BaseModel):
    screen_id: int
    movies: List[MovieQuota]

class HybridScheduleRequest(BaseModel):
    start_date:  date
    days:  int = Field(gt=0, le=31)
    buffer_minutes: int = Field(gt=0, le=60)
    default_open_time:  time
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

def round_time_to_nearest_5(t: time) -> time:
    """
    Round a time to the nearest 5-minute interval.
    
    Examples: 
        3:01 -> 3:00
        3:03 -> 3:05
        3:08 -> 3:10
        3:12 -> 3:10
        3:58 -> 4:00
    """
    total_minutes = t. hour * 60 + t.minute
    # Round to nearest 5 minutes
    rounded_minutes = round(total_minutes / 5) * 5
    
    # Handle overflow past midnight
    if rounded_minutes >= 24 * 60:
        rounded_minutes = 23 * 60 + 55  # Cap at 23:55
    
    new_hour = rounded_minutes // 60
    new_minute = rounded_minutes % 60
    
    return time(hour=new_hour, minute=new_minute, second=0)


def minutes_between(start_t: time, end_t: time) -> int:
    dt_start = datetime.combine(date.today(), start_t)
    dt_end = datetime. combine(date.today(), end_t)
    return max(0, int((dt_end - dt_start).total_seconds() // 60))


def add_minutes(base:  time, minutes: int) -> time:
    """
    Add minutes to a time and round to nearest 5-minute interval. 
    """
    dt = datetime.combine(date.today(), base) + timedelta(minutes=minutes)
    result = dt. time()
    return round_time_to_nearest_5(result)


def show_exists(db: Session, screen_id: int, show_date: date, start_time: time) -> bool:
    """
    Check for existence using the Show ORM mapping (new schema).
    """
    try:
        return db.query(Show).filter(
            Show.screen_id == screen_id,
            Show. show_date == show_date,
            Show.show_time == start_time
        ).first() is not None
    except Exception: 
        try:
            return db.query(Show).filter(
                Show.screen_id == screen_id,
                Show.show_date == show_date,
                Show.show_time == start_time
            ).first() is not None
        except Exception:
            return False


# ===================== Free Window Construction =====================

def build_free_windows(
    open_time: time,
    close_time: time,
    existing:  List[Tuple[time, time]],
    buffer:  int
) -> List[Tuple[time, time]]:
    """
    Build non-overlapping free windows between existing shows.
    existing: list of (start_time, end_time) for already scheduled shows (sorted).
    Buffer is respected by shrinking windows so new shows never violate turnaround
    relative to existing shows. 
    """
    windows:  List[Tuple[time, time]] = []
    existing_sorted = sorted(existing, key=lambda x:  x[0])

    current_start = open_time
    for (s, e) in existing_sorted:
        window_end_candidate = add_minutes(s, -buffer) if buffer > 0 else s
        if window_end_candidate > current_start:
            windows.append((current_start, window_end_candidate))
        next_start = add_minutes(e, buffer) if buffer > 0 else e
        if next_start > current_start: 
            current_start = next_start

    if current_start < close_time:
        windows.append((current_start, close_time))

    filtered = [(ws, we) for (ws, we) in windows if ws < we]
    return filtered


def greedy_day_schedule_with_windows(
    day: date,
    screen:  Screen,
    quotas: List[MovieQuota],
    movies_lookup: Dict[int, Movie],
    buffer: int,
    filler_pool: List[int],
    warnings: List[WarningEntry],
    open_default:  time,
    close_default: time,
    existing_shows: List[Show]
) -> List[Dict[str, Any]]:
    """
    Schedules quota & filler movies inside free windows derived from existing shows. 
    existing_shows: persisted shows already on this screen/day (immutable).
    All show times are rounded to nearest 5-minute intervals.
    """
    open_time:  time = getattr(screen, "open_time", None) or open_default
    close_time:  time = getattr(screen, "close_time", None) or close_default

    # Round open and close times to nearest 5 minutes
    open_time = round_time_to_nearest_5(open_time)
    close_time = round_time_to_nearest_5(close_time)

    if open_time >= close_time: 
        warnings.append(WarningEntry(
            code="INVALID_WINDOW",
            message=f"Screen {screen.screen_id} has invalid times; skipping day.",
            context={"day": str(day)}
        ))
        return []

    existing_intervals:  List[Tuple[time, time]] = [(show.show_time, show. end_time) for show in existing_shows]
    free_windows = build_free_windows(open_time, close_time, existing_intervals, buffer)

    if not free_windows:
        warnings.append(WarningEntry(
            code="NO_FREE_WINDOWS",
            message="All time is occupied by existing shows.",
            context={"screen_id": screen. screen_id, "day": str(day)}
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
                context={"screen_id": screen. screen_id, "day": str(day)}
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
            "movie_id": q. movie_id,
            "min":  q.min_shows_per_day,
            "max":  q.max_shows_per_day if q.max_shows_per_day is not None else float("inf"),
            "duration":  duration,
            "scheduled":  0
        })

    # Sort quotas by descending duration to reduce fragmentation (heuristic)
    prepared.sort(key=lambda x: x["duration"], reverse=True)

    # Filler candidates (include zero-min quota movies + global filler pool)
    filler_candidates = list({*filler_pool, *[p["movie_id"] for p in prepared if p["min"] == 0]})
    filler_candidates = [
        m for m in filler_candidates
        if movies_lookup.get(m) and (movies_lookup[m]. duration or 0) > 0
    ]
    filler_candidates. sort(key=lambda mid: movies_lookup[mid]. duration or 0)

    def can_place_quota_entry(entry) -> bool:
        return entry["scheduled"] < entry["max"]

    def still_unmet_min(entry) -> bool:
        return entry["scheduled"] < entry["min"]

    schedule:  List[Dict[str, Any]] = []

    # Iterate over each free window independently
    for (w_start, w_end) in free_windows:
        # Round window start to nearest 5 minutes
        current_time = round_time_to_nearest_5(w_start)

        def fits(movie_id: int, now: time, window_end: time) -> bool:
            movie = movies_lookup[movie_id]
            dur = movie.duration or 0
            if dur <= 0:
                return False
            remaining = minutes_between(now, window_end)
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
                start_t = round_time_to_nearest_5(current_time)
                end_t = add_minutes(start_t, movie.duration)
                schedule. append({
                    "date": day,
                    "start": start_t. strftime("%H:%M"),
                    "end": end_t.strftime("%H:%M"),
                    "movie_id": entry["movie_id"],
                    "screen_id": screen.screen_id,
                })
                entry["scheduled"] += 1
                next_time = add_minutes(end_t, buffer)
                if next_time > w_end: 
                    current_time = end_t
                    placed = True
                    break
                current_time = next_time
                placed = True
            if not placed: 
                break

        # PHASE 2: Additional quota up to max, else fillers
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
                start_t = round_time_to_nearest_5(current_time)
                end_t = add_minutes(start_t, movie. duration)
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
                leftover = minutes_between(current_time, w_end)
                if leftover > 0:
                    warnings.append(WarningEntry(
                        code="LEFTOVER_GAP",
                        message="Unfilled gap in window; no movie fits.",
                        context={
                            "screen_id": screen. screen_id,
                            "day":  str(day),
                            "gap_minutes": leftover,
                            "window_start": w_start.strftime("%H:%M"),
                            "window_end": w_end.strftime("%H:%M")
                        }
                    ))
                break
            movie = movies_lookup[filler_candidate]
            start_t = round_time_to_nearest_5(current_time)
            end_t = add_minutes(start_t, movie.duration)
            schedule.append({
                "date": day,
                "start": start_t. strftime("%H:%M"),
                "end": end_t.strftime("%H:%M"),
                "movie_id":  filler_candidate,
                "screen_id": screen.screen_id,
            })
            next_time = add_minutes(end_t, buffer)
            current_time = end_t if next_time > w_end else next_time

        if safety >= 500:
            warnings.append(WarningEntry(
                code="WINDOW_SAFETY_ABORT",
                message="Aborted scheduling inside window due to safety iteration cap.",
                context={"screen_id":  screen.screen_id, "day": str(day),
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
                    "screen_id": screen. screen_id,
                    "day":  str(day),
                    "scheduled": entry["scheduled"],
                    "min": entry["min"]
                }
            ))
        if entry["scheduled"] > entry["max"]:
            warnings. append(WarningEntry(
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
    """
    Persist schedule rows into the DB using the Show ORM model.
    """
    added_any = False
    for item in rows:
        try:
            show_date = item["date"]
            if isinstance(show_date, str):
                show_date = datetime. strptime(show_date, "%Y-%m-%d").date()
            start_t = item["start"]
            if isinstance(start_t, str):
                start_time = datetime.strptime(start_t, "%H:%M").time()
            else:
                start_time = start_t
            # Round the start time to nearest 5 minutes
            start_time = round_time_to_nearest_5(start_time)
        except Exception as e:
            warnings.append(WarningEntry(
                code="PARSE_ERROR",
                message="Malformed schedule entry skipped.",
                context={"entry": str(item), "error": str(e)}
            ))
            continue

        try:
            movie_id = int(item. get("movie_id"))
            screen_id = int(item.get("screen_id"))
        except Exception as e: 
            warnings.append(WarningEntry(
                code="MALFORMED_IDS",
                message="movie_id or screen_id missing/invalid; entry skipped.",
                context={"entry":  str(item), "error": str(e)}
            ))
            continue

        end_time = None
        try:
            end_raw = item.get("end")
            if end_raw: 
                if isinstance(end_raw, str):
                    end_time = datetime.strptime(end_raw, "%H:%M").time()
                else:
                    end_time = end_raw
                # Round end time to nearest 5 minutes
                end_time = round_time_to_nearest_5(end_time)
            else:
                movie = None
                try:
                    movie = db.get(Movie, movie_id)
                except Exception: 
                    movie = None
                if movie is None:
                    movie = db.query(Movie).filter(
                        getattr(Movie, "id", Movie.movie_id) == movie_id
                    ).first()
                if movie is None: 
                    warnings.append(WarningEntry(
                        code="MISSING_MOVIE",
                        message=f"Movie {movie_id} not found while deriving end_time; entry skipped.",
                        context={"movie_id": movie_id, "entry": str(item)}
                    ))
                    continue
                dur = getattr(movie, "duration", None) or 0
                if dur <= 0:
                    warnings. append(WarningEntry(
                        code="INVALID_DURATION",
                        message=f"Cannot derive end_time because movie {movie_id} duration is missing/non-positive; entry skipped.",
                        context={"movie_id": movie_id, "duration": dur}
                    ))
                    continue
                end_time = add_minutes(start_time, dur)
        except Exception as e:
            warnings. append(WarningEntry(
                code="END_PARSE_ERROR",
                message="Failed to parse/derive end_time; entry skipped.",
                context={"entry":  str(item), "error": str(e)}
            ))
            continue

        if end_time is None:
            warnings. append(WarningEntry(
                code="MISSING_END_TIME",
                message="end_time could not be determined; entry skipped.",
                context={"entry": str(item)}
            ))
            continue

        if show_exists(db, screen_id, show_date, start_time):
            warnings.append(WarningEntry(
                code="DUPLICATE_SHOW",
                message="Show already exists; skipped.",
                context={"screen_id": screen_id, "date": str(show_date), "start": item. get("start")}
            ))
            continue

        fmt = item.get("format") or "2D"
        lang = item.get("language")

        if isinstance(lang, (list, tuple)):
            chosen = None
            for el in lang:
                if isinstance(el, str) and el.strip():
                    chosen = el. strip()
                    break
                if isinstance(el, (list, tuple)):
                    for sub in el:
                        if isinstance(sub, str) and sub.strip():
                            chosen = sub.strip()
                            break
                    if chosen: 
                        break
            lang = chosen

        if not lang:
            try:
                movie = None
                try: 
                    movie = db.get(Movie, movie_id)
                except Exception: 
                    movie = None
                if movie is None:
                    movie = db.query(Movie).filter(
                        getattr(Movie, "id", Movie.movie_id) == movie_id
                    ).first()
                if movie is None: 
                    warnings.append(WarningEntry(
                        code="MISSING_MOVIE",
                        message=f"Movie {movie_id} not found while persisting show; language left unset.",
                        context={"movie_id":  movie_id, "entry": str(item)}
                    ))
                    lang = None
                else: 
                    movie_languages = getattr(movie, "languages", None)
                    if movie_languages: 
                        if isinstance(movie_languages, (list, tuple)) and len(movie_languages) > 0:
                            lang = movie_languages[0]
                        elif isinstance(movie_languages, str) and movie_languages: 
                            lang = movie_languages
                        else:
                            lang = None
                    else: 
                        lang = getattr(movie, "language", None)

                    if isinstance(lang, (list, tuple)):
                        for el in lang:
                            if isinstance(el, str) and el.strip():
                                lang = el. strip()
                                break
                    if not lang: 
                        warnings.append(WarningEntry(
                            code="MISSING_MOVIE_LANGUAGE",
                            message=f"Movie {movie_id} has no language info; persisted show will have no language set.",
                            context={"movie_id": movie_id, "entry": str(item)}
                        ))
            except Exception as e: 
                warnings.append(WarningEntry(
                    code="MOVIE_LOOKUP_FAILED",
                    message="Failed to lookup Movie while deriving language.",
                    context={"movie_id":  movie_id, "error": str(e)}
                ))
                lang = None

        status_val = item.get("status")
        if status_val is None:
            status = ShowStatus.UPCOMING
        else:
            try:
                if isinstance(status_val, ShowStatus):
                    status = status_val
                elif isinstance(status_val, str) and status_val in ShowStatus.__members__:
                    status = ShowStatus[status_val]
                else:
                    status = ShowStatus(status_val)
            except Exception: 
                status = ShowStatus. UPCOMING

        try: 
            show_obj = Show(
                movie_id=movie_id,
                screen_id=screen_id,
                show_date=show_date,
                show_time=start_time,
                end_time=end_time,
                status=status,
                format=(fmt if fmt is not None else "2D"),
                language=(lang if lang is not None else None)
            )
            db.add(show_obj)
            added_any = True
        except Exception as e:
            warnings. append(WarningEntry(
                code="PERSIST_ERROR",
                message="Failed to add show to the session.",
                context={"entry": str(item), "error": str(e)}
            ))
            continue

    if added_any: 
        try:
            db. commit()
        except Exception as e: 
            try:
                db. rollback()
            except Exception:
                pass
            warnings.append(WarningEntry(
                code="DB_COMMIT_FAILED",
                message="Failed to commit scheduled shows.",
                context={"error": str(e)}
            ))
            raise


