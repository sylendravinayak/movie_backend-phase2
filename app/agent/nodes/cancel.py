"""
Production-Ready Show Cancellation
- Revenue-aware decisions
- Customer impact consideration
- Refund tracking
- Safety checks
"""
from datetime import datetime, timedelta
from database import SessionLocal
from model import Show, Seat
from model.theatre import ShowStatusEnum
from model.seat import SeatLock, SeatLockStatusEnum
from agent.state import OpsState
from sqlalchemy import text


def calculate_refund_amount(show_id: int, db) -> float:
    """Calculate total refund if show is cancelled"""
    refund = db.execute(text("""
        SELECT COALESCE(SUM(scp.price), 0) as refund
        FROM booked_seats bs
        JOIN seats s ON bs.seat_id = s.seat_id
        JOIN show_category_pricing scp ON 
            scp.show_id = bs.show_id AND 
            scp.category_id = s.category_id
        WHERE bs.show_id = :show_id
        AND bs.status = 'BOOKED'
    """), {"show_id": show_id}).scalar()
    
    return float(refund or 0)


def calculate_opportunity_cost(show_id: int, db) -> float:
    """Calculate lost revenue potential from cancellation"""
    potential = db.execute(text("""
        SELECT COALESCE(SUM(scp.price), 0) as potential
        FROM seats s
        JOIN show_category_pricing scp ON 
            scp.show_id = :show_id AND 
            scp.category_id = s.category_id
        JOIN shows sh ON sh.show_id = :show_id
        WHERE s.screen_id = sh.screen_id
    """), {"show_id": show_id}).scalar()
    
    current_revenue = db.execute(text("""
        SELECT COALESCE(SUM(scp.price), 0) as revenue
        FROM booked_seats bs
        JOIN seats s ON bs.seat_id = s.seat_id
        JOIN show_category_pricing scp ON 
            scp.show_id = bs.show_id AND 
            scp.category_id = s.category_id
        WHERE bs.show_id = :show_id
        AND bs.status = 'BOOKED'
    """), {"show_id": show_id}).scalar()
    
    # Opportunity cost = what we could have made - what we already made
    return float(potential or 0) - float(current_revenue or 0)


def process_refunds(show_id: int, db) -> int:
    """
    Process refunds for cancelled show
    Returns: number of customers affected
    """
    # Update booked seats to refunded status
    affected = db.execute(text("""
        UPDATE booked_seats
        SET status = 'REFUNDED'
        WHERE show_id = :show_id
        AND status = 'BOOKED'
    """), {"show_id": show_id})
    
    return affected.rowcount


def cancel_node(state: OpsState):
    """
    Intelligent show cancellation with revenue tracking
    """
    db = SessionLocal()
    now = datetime.utcnow()
    
    # Build forecast map
    forecast_map = {}
    for s in state.get("result", {}).get("scheduling", []):
        if s.get("show_id"):
            forecast_map[s["show_id"]] = s
    
    # Get upcoming shows (next 48 hours)
    cutoff_date = datetime.now() + timedelta(hours=48)
    
    shows = db.query(Show).filter(
        Show.status == ShowStatusEnum.UPCOMING,
        Show.show_date <= cutoff_date.date()
    ).all()
    
    cancelled = []
    total_refunds = 0
    total_customers_affected = 0
    total_opportunity_lost = 0
    
    for show in shows:
        # Get forecast if available
        forecast = forecast_map.get(show.show_id)
        if not forecast:
            # No forecast = can't make decision
            continue
        
        show_dt = datetime.combine(show.show_date, show.show_time)
        hours_left = (show_dt - now).total_seconds() / 3600
        
        # Safety: Never cancel within 3 hours
        if hours_left < 3:
            continue
        
        # Get capacity
        total_seats = db.query(Seat).filter(
            Seat.screen_id == show.screen_id
        ).count() or 1
        
        # Get current bookings
        booked = db.query(SeatLock).filter(
            SeatLock.show_id == show.show_id,
            SeatLock.status == SeatLockStatusEnum.BOOKED
        ).count()
        
        current_occ = booked / total_seats
        
        # Get forecast metrics
        forecast_demand = forecast.get("forecast_demand", 0)
        forecast_occ = forecast_demand / total_seats
        confidence = forecast.get("confidence", 0.5)
        
        gap = forecast_occ - current_occ
        
        # Calculate financial impact
        refund_amount = calculate_refund_amount(show.show_id, db)
        opportunity_cost = calculate_opportunity_cost(show.show_id, db)
        
        # =============== CANCELLATION DECISION ===============
        
        # Criteria for cancellation:
        # 1. Severe underperformance (gap < -40%)
        # 2. Very low occupancy (< 5%)
        # 3. Sufficient time to notify customers (> 6 hours)
        # 4. High confidence in forecast (> 60%)
        # 5. Opportunity cost is minimal (we won't miss out on revenue)
        
        should_cancel = (
            gap < -0.40 and
            current_occ < 0.05 and
            hours_left > 6 and
            confidence > 0.60 and
            opportunity_cost < refund_amount * 0.5  # Not worth keeping
        )
        
        # Additional check: Don't cancel if already decent bookings
        if current_occ > 0.10:
            should_cancel = False
        
        if should_cancel:
            # Process cancellation
            customers_affected = process_refunds(show.show_id, db)
            
            show.status = ShowStatusEnum.CANCELLED
            
            cancelled.append({
                "show_id": show.show_id,
                "movie": forecast.get("movie", "Unknown"),
                "date": str(show.show_date),
                "time": str(show.show_time),
                "gap": round(gap, 2),
                "current_occupancy": round(current_occ, 2),
                "forecast_occupancy": round(forecast_occ, 2),
                "hours_left": round(hours_left, 1),
                "confidence": confidence,
                "customers_affected": customers_affected,
                "refund_amount": round(refund_amount, 2),
                "opportunity_cost": round(opportunity_cost, 2),
                "total_loss": round(refund_amount + opportunity_cost, 2),
                "reason": "severe_underperformance"
            })
            
            total_refunds += refund_amount
            total_customers_affected += customers_affected
            total_opportunity_lost += opportunity_cost
    
    db.commit()
    db.close()
    
    state.setdefault("result", {})
    state["result"]["cancelled"] = cancelled
    state["result"]["cancellation_summary"] = {
        "total_shows_cancelled": len(cancelled),
        "total_customers_affected": total_customers_affected,
        "total_refunds": round(total_refunds, 2),
        "total_opportunity_lost": round(total_opportunity_lost, 2),
        "total_revenue_impact": round(-(total_refunds + total_opportunity_lost), 2)
    }
    
    if cancelled:
        state["output"] = (
            f"Cancellations: {len(cancelled)} shows cancelled. "
            f"{total_customers_affected} customers affected. "
            f"Refunds: ₹{round(total_refunds, 2)}. "
            f"Total revenue impact: ₹{round(-(total_refunds + total_opportunity_lost), 2)}"
        )
    else:
        state["output"] = "No shows cancelled."
    
    return state