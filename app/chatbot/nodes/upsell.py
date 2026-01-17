from __future__ import annotations

from chatbot.state import ChatState

# Deterministic upsell list (no LLM decisions)
DEFAULT_UPSELL = [
    "Popcorn combo",
    "Cold drink",
    "Nachos with cheese",
]


async def offer_upsell(state: ChatState) -> ChatState:
    if state.get("awaiting_user"):
        return state
    state["upsell_suggestions"] = DEFAULT_UPSELL
    state["response"] = (
        "I can add snacks too. Popular options: "
        + ", ".join(DEFAULT_UPSELL)
        + ". Should I proceed with the tickets now?"
    )
    return state