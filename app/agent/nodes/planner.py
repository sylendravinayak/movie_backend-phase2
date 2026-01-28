from langchain_groq import ChatGroq
from sqlalchemy import text
from app.agent.state import OpsState
from crud.log_agent_crud import agent_log_crud
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from typing import List, Optional
from database import SessionLocal
class PlannerDecision(BaseModel):
    route: str = Field(description="Which agent route to take")
    movies: Optional[List[str]] = Field(
        default=None,
        description="Movie name if mentioned in request"
    )
    show_id: Optional[int] = Field(
        default=None,
        description="Show ID if explicitly mentioned"
    )
    reason: str = Field(description="Why this route was chosen")
    confidence: float = Field(description="Confidence between 0 and 1")


parser = PydanticOutputParser(pydantic_object=PlannerDecision)
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
PLANNER_PROMPT = """
You are a movie theater operations planner.

Decide which agent should handle the request.

Routes:
optimize(reschedule shows to maximize revenue)
pricing
scheduling
forecast
{format_instructions}

Request: {request}
"""

def planner_node(state: OpsState):
    db= SessionLocal()
    prompt = PLANNER_PROMPT.format(
        request=state["input"],
        format_instructions=parser.get_format_instructions()
    )

    resp = llm.invoke(prompt)

    decision = parser.parse(resp.content)

    decision_dict = decision.model_dump()
    rows = db.execute(text("""
    SELECT
        movie_id,
        AVG(
            LEAST(1.3, GREATEST(0.7, actual_bookings::float / forecast_demand))
        ) AS correction_factor
    FROM forecast_history
    WHERE actual_bookings IS NOT NULL
      AND forecast_demand > 0
    GROUP BY movie_id
""")).fetchall()

    correction_map = {
    r.movie_id: round(r.correction_factor, 2)
    for r in rows
}

    state["decision"] = decision_dict
    print( "Planner decision:", decision_dict )
    state["show_id"]= decision.show_id

    state["correction_map"] = correction_map
    db.close()
    return state