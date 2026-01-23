from datetime import date
from database import SessionLocal
from agent.state import OpsState
from sqlalchemy import text


def feedback_node(state: OpsState):

    db = SessionLocal()
    today = date.today()

    # ---- Update actual bookings per show ----
    db.execute(text("""
        UPDATE forecast_history f
        SET actual_bookings = sub.actual_bookings
        FROM (
            SELECT
                s.show_id,
                COUNT(b.booking_id) AS actual_bookings
            FROM shows s
            LEFT JOIN bookings b ON b.show_id = s.show_id
            WHERE s.show_date < :today
            GROUP BY s.show_id
        ) sub
        WHERE f.show_id = sub.show_id
    """), {"today": today})

    db.commit()

    # ---- Read completed forecasts ----
    rows = db.execute(text("""
        SELECT
            show_id,
            movie_id,
            target_date,
            forecast_demand,
            actual_bookings,
            confidence
        FROM forecast_history
        WHERE target_date < :today
          AND actual_bookings IS NOT NULL
    """), {"today": today}).fetchall()

    feedback = []
    correction_map = {}

    for r in rows:

        predicted = r.forecast_demand or 0
        actual = r.actual_bookings or 0

        error = abs(actual - predicted) / max(predicted, 1)

        ratio = actual / max(predicted, 1)

        # clamp correction
        ratio = min(max(ratio, 0.7), 1.3)

        feedback.append({
            "show_id": r.show_id,
            "movie_id": r.movie_id,
            "date": str(r.target_date),
            "forecast": predicted,
            "actual": actual,
            "error": round(error, 2),
            "correction_factor": round(ratio, 2),
            "confidence": r.confidence
        })

        correction_map.setdefault(r.movie_id, []).append(ratio)

    # ---- Aggregate correction per movie ----
    movie_corrections = {
        m: round(sum(v)/len(v), 2)
        for m, v in correction_map.items()
    }

   
    db.commit()
    db.close()

    # ---- Return learning to system ----
    state.setdefault("result", {})
    
    

    return state
