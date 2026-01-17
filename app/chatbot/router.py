from __future__ import annotations
from typing import Dict, Any
from chatbot.main_graph import graph_app
from chatbot.state import ChatState


async def run_graph(message: str, user_id: int | None, prior_state: Dict[str, Any] | None = None) -> ChatState:
    state: ChatState = prior_state.copy() if prior_state else {}
    state["message"] = message
    if user_id is not None:
        state["user_id"] = user_id

    result: ChatState = await graph_app.ainvoke(state)
    return result