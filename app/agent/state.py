from typing import TypedDict, Optional, Dict, Any

class OpsState(TypedDict):
    intent: Optional[str]
    input: Optional[str]
    show_id: Optional[int]
    movies: Optional[list[str]]
    decision: Dict[str, Any]
    result: Dict[str, Any]
    approved: bool
