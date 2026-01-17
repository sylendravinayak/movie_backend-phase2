from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from chatbot.router import run_graph
from utils.auth.jwt_bearer import JWTBearer

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    user_id: Optional[int] = None
    message: str
    state: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    state: Dict[str, Any]


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    auth: dict = Depends(JWTBearer()),
):
    """
    Chat endpoint that injects the incoming Authorization header into the conversation state
    so nodes (e.g. cancel flow) can forward the user's JWT to internal APIs when needed.

    - Ensures payload.state is a dict.
    - Copies the Authorization header (if present) into state["auth_token"].
    - Ensures state["user_id"] is populated from payload.user_id or auth payload if available.
    """
    if not payload.message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Ensure we have a mutable dict for state
    state: Dict[str, Any] = dict(payload.state or {})

    # Copy Authorization header into state so nodes can forward it when needed
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        # Keep full header (e.g. "Bearer <token>") since the cancel node knows how to parse it
        state["auth_token"] = auth_header.strip()

    # If the JWTBearer dependency returned an auth dict with user info, prefer it for user_id
    # (but don't override an explicit payload.user_id sent by client)
    if payload.user_id is None:
        # common keys in auth payload might be 'user_id', 'sub', 'id'
        for k in ("user_id", "sub", "id"):
            if isinstance(auth, dict) and k in auth and auth[k] is not None:
                try:
                    state["user_id"] = int(auth[k])
                except Exception:
                    state["user_id"] = auth[k]
                break
    else:
        state["user_id"] = payload.user_id

    # Run the chat graph with the enriched state
    graph_state = await run_graph(payload.message, state.get("user_id"), state)

    resp = graph_state.get("response") or "Sorry, I couldn't process that."
    # Ensure we return a dict for state in the response model
    return ChatResponse(response=resp, state=dict(graph_state or {}))