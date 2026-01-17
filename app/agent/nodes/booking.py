from sqlalchemy.orm import Session
from database import SessionLocal
from model import BookedSeat
from app.agent.state import OpsState
from crud.log_agent_crud import agent_log_crud

def booking_node(state: OpsState):
    db: Session = SessionLocal()

    show_id = state["show_id"]
    
    conflicts = db.query(BookedSeat).filter_by(show_id=show_id).all()

    result = {"conflicts": len(conflicts)}

    db.close()

    agent_log_crud.log_booking_check({
        "show_id": show_id,
        "conflicts_found": len(conflicts)
    })
    state["result"] = result
    return state
