from __future__ import annotations

from langgraph.graph import StateGraph
from chatbot.state import ChatState
from chatbot.nodes.extract import extract_entities
from chatbot.nodes.validate import validate_booking_request
from chatbot.nodes.screen import resolve_screen
from chatbot.nodes.showtime import resolve_showtime
from chatbot.nodes.seats import handle_seats_and_lock
from chatbot.nodes.upsell import offer_upsell
from chatbot.nodes.confirm import confirm_booking


booking_graph = StateGraph(ChatState)

booking_graph.add_node("validate", validate_booking_request)
booking_graph.add_node("screen", resolve_screen)
booking_graph.add_node("showtime", resolve_showtime)
booking_graph.add_node("seat", handle_seats_and_lock)
booking_graph.add_node("upsell", offer_upsell)
booking_graph.add_node("confirm", confirm_booking)

booking_graph.set_entry_point("validate")
booking_graph.add_edge("validate", "screen")
booking_graph.add_edge("screen", "showtime")
booking_graph.add_edge("showtime", "seat")
booking_graph.add_edge("seat", "upsell")
booking_graph.add_edge("upsell", "confirm")

booking_app = booking_graph.compile()