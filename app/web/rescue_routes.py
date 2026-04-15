from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..database import get_db, get_or_create_user
from ..application.rescue_chat_surface import apply_rescue_chat_action, build_rescue_chat_surface

router = APIRouter()


class RescueChatActionRequest(BaseModel):
    user_id: str
    action: Literal[
        "accept_rescue_plan",
        "shorten_rescue_plan",
        "extend_rescue_plan",
        "defer_rescue_plan",
        "reject_rescue_plan",
        "explain_rescue_plan",
    ]
    reject_reason: str | None = None
    reason: str | None = None


@router.get("/rescue/chat")
def rescue_chat_surface(
    user_id: str,
    mode: Literal["proactive", "reactive_explicit_rescue_request"] = "proactive",
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, user_id)
    result = build_rescue_chat_surface(db, user_id=user.id, mode=mode)
    return {
        "surfaced": result.surfaced,
        "proposal_container_id": result.proposal_container_id,
        "proposal_status": result.proposal_status,
        "response": asdict(result.response),
        "writeback": result.writeback,
    }


@router.post("/rescue/chat/action")
def rescue_chat_action(
    request: RescueChatActionRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    result = apply_rescue_chat_action(
        db,
        user_id=user.id,
        action=request.action,
        reject_reason=request.reject_reason,
        reason=request.reason,
    )
    return {
        "surfaced": result.surfaced,
        "proposal_container_id": result.proposal_container_id,
        "proposal_status": result.proposal_status,
        "response": asdict(result.response),
        "writeback": result.writeback,
    }
