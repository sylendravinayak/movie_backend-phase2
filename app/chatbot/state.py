from __future__ import annotations

from typing import List, Optional, TypedDict, Literal, Dict, Any
from datetime import date, time, datetime


Intent = Literal["booking", "recommendation", "screen_info", "fallback"]


class ChatState(TypedDict, total=False):
    # Inputs
    user_id: Optional[int]
    message: str

    # LLM-extracted entities
    intent: Optional[Intent]
    movie_title: Optional[str]
    movie_id: Optional[int]
    screen_id: Optional[int]
    screen_name: Optional[str]
    show_id: Optional[int]
    show_date: Optional[date]
    show_time: Optional[time]
    language: Optional[str]
    format: Optional[str]
    seats_requested: Optional[int]
    seat_ids: List[int]
    available_seats: List[str]
    show_options: List[Dict[str, Any]]
    auth_token: Optional[str]
    # Flow control
    missing_fields: List[str]
    awaiting_user: bool
    next_node: Optional[str]

    # Outputs
    response: Optional[str]
    upsell_suggestions: List[str]
    booking_id: Optional[int]
    booking_reference: Optional[str]
    meta: Dict[str, Any]