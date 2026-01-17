from langgraph.errors import Interrupt
from agent.state import OpsState
def approval_node(state: OpsState):
    if state["decision"]["confidence"] < 0.8 and not state.get("approved"):
        raise Interrupt("Human approval required")
    return state
