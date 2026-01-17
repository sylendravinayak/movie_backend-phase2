from __future__ import annotations

from langgraph.graph import StateGraph
from chatbot.state import ChatState, Intent
from chatbot.nodes.extract import extract_entities
from chatbot.booking_graph import booking_app
from chatbot.nodes.cancel import handle_cancel_via_http


async def route_intent(state: ChatState) -> ChatState:
    intent: Intent | None = state.get("intent") or "fallback"

    # Always invoke the booking flow when intent==booking.
    # Node-level awaiting_user checks prevent nodes from overriding earlier interrupts.
    if intent == "cancel":
        return await handle_cancel_via_http(state)
    
    if intent == "booking":
        return await booking_app.ainvoke(state)

    if intent == "recommendation":
        state["response"] = (
            "I can suggest movies now. Please tell me a movie title, genre, or language preference."
        )
        return state
    if intent == "screen_info":
        state["response"] = "Which movie and date do you want screen info for?"
        return state
    state["response"] = "Sorry, I didn't get that. You can say things like 'Book 2 tickets for Inception tomorrow 7pm'."
    return state


graph = StateGraph(ChatState)
graph.add_node("extract", extract_entities)
graph.add_node("route", route_intent)

graph.set_entry_point("extract")
graph.add_edge("extract", "route")

graph_app = graph.compile()