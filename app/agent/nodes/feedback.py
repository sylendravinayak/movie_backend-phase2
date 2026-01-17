from datetime import date
from database import SessionLocal
from agent.state import OpsState
from sqlalchemy import text


def feedback_node(state: OpsState):

    db = SessionLocal()
    today = date.today()

   
    db.execute(text("""
        UPDATE forecast_history f
        SET actual_bookings = sub.actual_bookings
        FROM (
            SELECT
                s.movie_id,
                s.show_date AS target_date,
                COUNT(b.booking_id) AS actual_bookings
            FROM shows s
            LEFT JOIN bookings b ON b.show_id = s.show_id
            WHERE s.show_date < :today
            GROUP BY s.movie_id, s.show_date
        ) sub
        WHERE f.movie_id = sub.movie_id
          AND f.target_date = sub.target_date
    """), {"today": today})

    db.commit()

    
    rows = db.execute(text("""
        SELECT
            movie_id,
            target_date,
            forecast_demand,
            actual_bookings
        FROM forecast_history
        WHERE target_date < :today
          AND actual_bookings IS NOT NULL
    """), {"today": today}).fetchall()

    feedback = []

    for r in rows:
        predicted = r.forecast_demand
        actual = r.actual_bookings or 0

        error = abs(actual - predicted) / max(predicted, 1)

        feedback.append({
            "movie_id": r.movie_id,
            "target_date": r.target_date,
            "forecast_demand": predicted,
            "actual_bookings": actual,
            "forecast_error": round(error, 2)
        })

    db.close()

    state["feedback"] = feedback
    state["output"] = f"Feedback computed for {len(feedback)} forecast records."

    return state
