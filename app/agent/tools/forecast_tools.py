from collections import Counter
from sqlalchemy import text



def seasonality_factor(date):
    if date.weekday() in [5, 6]:
        return 1.3
    return 1.0


def forecast_from_trend(blended, season):
    base_capacity = 3   # your business constant
    return round(max(base_capacity * blended * season, 1))


def get_slot_factor(movie_id, show_time, db):
    hour = show_time.hour

    rows = db.execute(text("""
        SELECT
            EXTRACT(HOUR FROM s.show_time) AS hr,
            COUNT(b.booking_id) AS bookings
        FROM shows s
        LEFT JOIN bookings b ON b.show_id = s.show_id
        WHERE s.movie_id = :movie_id
        GROUP BY hr
    """), {"movie_id": movie_id}).fetchall()

    if not rows:
        return 1.0

    slot_map = {int(r.hr): r.bookings for r in rows}

    total = sum(slot_map.values())
    avg = total / len(slot_map) if total else 1

    return round(slot_map.get(hour, avg) / avg, 3)


def compute_velocity(series):
    if len(series) < 2:
        return 1.0

    unique_days = len(set(series))
    return min(2.0, len(series) / unique_days)


def normalize_external_trend(score):
    return 1 + (score - 1) * 0.25


def compute_confidence(velocity, slot_factor, external):

    # all factors near 1 → high confidence
    dispersion = abs(velocity - 1) + abs(slot_factor - 1) + abs(external - 1)

    confidence = 1 - (dispersion / 3)

    return round(max(0.4, min(confidence, 0.95)), 2)

