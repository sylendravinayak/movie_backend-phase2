from langgraph.errors import NodeInterrupt
from agent.state import OpsState

def approval_node(state: OpsState):

    decision = state["decision"]


    if decision.get("confidence", 0) < 0.7 and not state.get("approved"):
        raise NodeInterrupt("Low confidence decision requires approval")

    return state

