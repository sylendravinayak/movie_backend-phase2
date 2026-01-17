from agent.state import OpsState
from agent.tools.occupancy import get_show_occupancy
from agent.tools.revenue import get_show_revenue
from agent.tools.pricing_policy import pricing_policy
from database import SessionLocal
from model import ShowCategoryPricing, SeatCategory, Show, Movie


def pricing_node(state: OpsState):

    db = SessionLocal()

    show_ids = set()

    if state.get("show_ids"):
        show_ids.update(state["show_ids"])

    if state.get("show_id"):
        show_ids.add(state["show_id"])

    scheduled = state.get("result", {}).get("scheduled_show_ids", [])
    for s in scheduled:
        show_ids.add(s)

    rescheduled = state.get("result", {}).get("reschedule", [])
    if rescheduled:
        show_ids=[r.get("show_id") for r in rescheduled ]


    movies = state.get("movies") or state.get("decision", {}).get("movies") 

    if movies and state["decision"].get("route") == "pricing":
        movie_rows = db.query(Movie).filter(Movie.title.in_(movies)).all()
        movie_ids = [m.movie_id for m in movie_rows]

        show_rows = db.query(Show.show_id).filter(
            Show.movie_id.in_(movie_ids)
        ).all()

        for s in show_rows:
            show_ids.add(s[0])

    show_ids = list(show_ids)

    pricing_results = []

    forecast_block = state.get("result", {}).get("forecast")

    for show_id in show_ids:

        forecast_demand = 1

        show = db.query(Show).filter(Show.show_id == show_id).first()

        if show and isinstance(forecast_block, list):
            for f in forecast_block:
                if f.get("movie_id") == show.movie_id:
                    forecast_demand = f.get("forecast_demand", 1)
                    break

        elif isinstance(forecast_block, dict):
            forecast_demand = forecast_block.get("forecast_demand", 1)

        occ = get_show_occupancy(show_id, db)
        revenue = get_show_revenue(show_id, db)

        pricing_rows = db.query(ShowCategoryPricing).filter(
            ShowCategoryPricing.show_id == show_id
        ).all()

      
        if not pricing_rows:
            categories = db.query(SeatCategory).all()

            for c in categories:
                row = ShowCategoryPricing(
                    show_id=show_id,
                    category_id=c.category_id,
                    price=c.base_price
                )
                db.add(row)
                pricing_rows.append(row)

            db.commit()

        updates = []

        for row in pricing_rows:

            base_price = db.query(SeatCategory.base_price).filter(
                SeatCategory.category_id == row.category_id
            ).scalar() or row.price

            old_price = float(row.price)

            new_price = pricing_policy(
                forecast_demand=forecast_demand,
                occupancy=occ,
                current_price=old_price,
                base_price=base_price
            )

            new_price=round(new_price/5)*5 
            row.price = new_price
            
            updates.append({
                "category_id": row.category_id,
                "old_price": old_price,
                "new_price": new_price
            })

        pricing_results.append({
            "show_id": show_id,
            "forecast_demand": forecast_demand,
            "occupancy": occ,
            "revenue": revenue,
            "pricing_updates": updates
        })

    db.commit()
    db.close()

    state.setdefault("result", {})
    state["result"]["pricing"] = pricing_results

    state["output"] = (
        f"Dynamic pricing applied for {len(pricing_results)} shows."
    )

    return state
