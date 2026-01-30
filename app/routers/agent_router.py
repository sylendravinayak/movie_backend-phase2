from fastapi import APIRouter
router = APIRouter(prefix="/agents", tags=["Agents"])
from agent.graph import agent_graph
import uuid
from langgraph.errors import Interrupt
from schemas import AgentRequest

@router.post("/operate")
def operate(req: AgentRequest):

    state = {
        "intent": req.intent,
        "movies": req.movies,
        "display_constraints": req.display_constraints or [],
        "forecast_days": req.forecast_days,
        "decision": {},
        "result": {}
    }

    thread_id = str(uuid.uuid4())

    try:
        return agent_graph.invoke(state, config={"thread_id": thread_id})
    except BaseException as i:
        if isinstance(i, Interrupt):
            return {
                    "status": "pending_approval",
                    "thread_id": thread_id,
                    "message": str(i)
                }
        else:
            raise i
        
@router.post("/approve/{thread_id}")
def approve(thread_id: str):
    return agent_graph.invoke(None, config={"thread_id": thread_id})
