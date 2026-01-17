from datetime import date
from sqlalchemy import text
from database import SessionLocal
from agent.state import OpsState

def reflection_node(state: OpsState):

    db = SessionLocal()
    today = date.today()

    rows = db.execute(text("""
        SELECT
            movie_id,
            forecast_demand,
            actual_bookings,
            forecast_error
        FROM forecast_history
        WHERE target_date < :today
          AND actual_bookings IS NOT NULL
    """), {"today": today}).fetchall()

    if not rows:
        state["result"]["reflection"] = {
            "message": "No historical data available for reflection yet.",
            "system_score": 5,
            "avg_error": None
        }
        db.close()
        return state

    errors = [r.forecast_error for r in rows if r.forecast_error is not None]

    avg_error = round(sum(errors) / len(errors), 3)

    if avg_error < 0.1:
        score = 9
    elif avg_error < 0.2:
        score = 8
    elif avg_error < 0.3:
        score = 7
    elif avg_error < 0.4:
        score = 6
    else:
        score = 5

    reflection_text = (
        f"Average forecast error is {avg_error}. "
        f"System learning quality score: {score}/10. "
    )

    if avg_error > 0.3:
        reflection_text += "Forecast model needs stronger correction tuning."
    elif avg_error > 0.15:
        reflection_text += "Forecast model is moderately accurate."
    else:
        reflection_text += "Forecast model is performing well."

    db.close()

    state["result"]["reflection"] = {
        "avg_error": avg_error,
        "system_score": score,
        "message": reflection_text
    }

    state["output"] = reflection_text

    return state
