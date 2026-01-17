from sqlalchemy.orm import Session
from sqlalchemy import func

def get_route_bias(route: str, db: Session):

    avg = db.execute("""
      SELECT AVG(score) FROM agent_learning WHERE route=:r
    """, {"r": route}).scalar()

    return float(avg or 7)
