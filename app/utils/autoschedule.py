from datetime import datetime, time, timedelta
from typing import List, Dict, Any


def generate_week_schedule(
    movies: List[Dict[str, int]],
    screens: List[Dict[str, int]],
    start_date,
    theatre_start: time,
    theatre_end: time,
    buffer: int = 15,
) -> List[Dict[str, Any]]:
    """
    Greedy, buffer-aware scheduler that fills each day's operating window for each screen.
    - movies: [{ "id": int, "duration": int_in_minutes }]
    - screens: [{ "id": int }]
    - start_date: datetime.date
    - theatre_start/theatre_end: datetime.time (operating window)
    - buffer: minutes gap between consecutive shows on the same screen

    Returns list of:
      {
        "date": "YYYY-MM-DD",
        "screen_id": int,
        "movie_id": int,
        "start": "HH:MM",
        "end": "HH:MM"
      }
    """
    if not movies or not screens:
        return []

    # Normalize durations to ints
    norm_movies = [{"id": int(m["id"]), "duration": int(m["duration"])} for m in movies]

    schedule: List[Dict[str, Any]] = []

    # Helper to combine a date and time and do minute arithmetic
    def dt_at(day, t: time) -> datetime:
        return datetime.combine(day, t)

    for day_offset in range(7):
        day_date = start_date + timedelta(days=day_offset)

        for screen in screens:
            screen_id = int(screen["id"])

            current_dt = dt_at(day_date, theatre_start)
            day_end_dt = dt_at(day_date, theatre_end)

            # Round-robin through movies, always picking the next that fits
            next_index = 0
            while True:
                placed = False

                # Try up to len(movies) choices from the current round-robin index
                for k in range(len(norm_movies)):
                    movie = norm_movies[(next_index + k) % len(norm_movies)]
                    duration_min = movie["duration"]
                    end_dt = current_dt + timedelta(minutes=duration_min)

                    # Fits entirely before closing time
                    if end_dt <= day_end_dt:
                        # Record the show
                        schedule.append({
                            "date": str(day_date),
                            "screen_id": screen_id,
                            "movie_id": movie["id"],
                            "start": current_dt.strftime("%H:%M"),
                            "end": end_dt.strftime("%H:%M"),
                        })

                        # Advance current time by duration + buffer
                        current_dt = end_dt + timedelta(minutes=buffer)
                        next_index = (next_index + k + 1) % len(norm_movies)
                        placed = True
                        break

                # If no movie fits in the remaining window, stop for this screen/day
                if not placed or current_dt >= day_end_dt:
                    break

    return schedule