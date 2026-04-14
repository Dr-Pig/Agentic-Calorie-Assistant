from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from ..models import User
from .canonical_commit_bridge import apply_proposal_decision_skeleton
from .open_proposals_read_model import build_open_rescue_proposals_view
from .rescue_overlay import apply_overlay_days_payload
from .rescue_response import RescuePlanAction, RescueResponseResult, apply_rescue_plan_action, build_rescue_response_result

RescueChatMode = Literal["proactive", "reactive_explicit_rescue_request"]


@dataclass(frozen=True)
class RescueChatSurfaceResult:
    surfaced: bool
    response: RescueResponseResult
    proposal_container_id: int | None = None
    proposal_status: str | None = None
    writeback: dict[str, Any] | None = None


def _empty_response(mode: str) -> RescueResponseResult:
    return RescueResponseResult(
        surfaced=False,
        reply_text="",
        recommended_days=None,
        daily_kcal_adjustment=None,
        overshoot_kcal=None,
        quick_actions=[],
        top_option=None,
        backup_options=[],
        ui_hints={"mode": mode},
    )


def build_rescue_chat_surface(
    db: Session,
    *,
    user_id: int,
    mode: RescueChatMode,
) -> RescueChatSurfaceResult:
    proposals = build_open_rescue_proposals_view(db, user_id=user_id)
    proposal = proposals[0] if proposals else None
    response = build_rescue_response_result(
        proposal=proposal,
        source="proactive" if mode == "proactive" else "reactive_explicit_rescue_request",
    )
    return RescueChatSurfaceResult(
        surfaced=response.surfaced,
        response=response,
        proposal_container_id=proposal.proposal_container_id if proposal is not None else None,
        proposal_status=proposal.proposal_status if proposal is not None else None,
        writeback=None,
    )


def _accept_rescue_writeback(
    db: Session,
    *,
    user_id: int,
    proposal: Any,
) -> dict[str, Any]:
    top_option = proposal.options[0] if proposal.options else None
    effect_payload = dict(top_option.effect_payload or {}) if top_option is not None else {}
    overlay_days = effect_payload.get("overlay_days")
    if not isinstance(overlay_days, list) or not overlay_days:
        return {
            "status": "skipped_non_overlay",
            "entry_ids": [],
        }

    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"user_id={user_id} not found")
    entries = apply_overlay_days_payload(
        db,
        user=user,
        overlay_days=overlay_days,
        safety_floor_kcal=int(effect_payload.get("safety_floor_kcal") or 0),
        source_id=proposal.proposal_container_id,
        source_type="rescue_proposal_accept",
        plan_viability=str(effect_payload.get("recovery_viability") or "viable"),  # type: ignore[arg-type]
    )
    return {
        "status": "applied",
        "entry_ids": [entry.id for entry in entries],
        "overlay_day_count": len(overlay_days),
    }


def apply_rescue_chat_action(
    db: Session,
    *,
    user_id: int,
    action: RescuePlanAction,
    reject_reason: str | None = None,
) -> RescueChatSurfaceResult:
    proposals = build_open_rescue_proposals_view(db, user_id=user_id)
    proposal = proposals[0] if proposals else None
    if proposal is None:
        return RescueChatSurfaceResult(
            surfaced=False,
            response=_empty_response("no_open_rescue_proposal"),
            proposal_container_id=None,
            proposal_status=None,
            writeback=None,
        )

    if action == "accept_rescue_plan":
        accepted_response = apply_rescue_plan_action(proposal=proposal, action=action)
        writeback = _accept_rescue_writeback(db, user_id=user_id, proposal=proposal)
        decision = apply_proposal_decision_skeleton(
            db,
            proposal_container_id=proposal.proposal_container_id,
            decision="accepted",
            metadata_patch={
                "last_chat_action": action,
                "accepted_option_id": proposal.top_option_id,
                "overlay_writeback": writeback,
            },
        )
        response = RescueResponseResult(
            surfaced=True,
            reply_text="好，我先把這個補回方案正式套上去。接下來我會用這個節奏幫你攤回來。",
            recommended_days=accepted_response.recommended_days,
            daily_kcal_adjustment=accepted_response.daily_kcal_adjustment,
            overshoot_kcal=accepted_response.overshoot_kcal,
            quick_actions=[],
            top_option=proposal.options[0] if proposal.options else None,
            backup_options=[],
            ui_hints={"mode": "rescue_accept_applied", "writeback_status": writeback["status"]},
        )
        return RescueChatSurfaceResult(
            surfaced=True,
            response=response,
            proposal_container_id=proposal.proposal_container_id,
            proposal_status=str(decision["proposal_status"]),
            writeback=writeback,
        )

    if action == "reject_rescue_plan" and reject_reason:
        decision = apply_proposal_decision_skeleton(
            db,
            proposal_container_id=proposal.proposal_container_id,
            decision="rejected",
            metadata_patch={
                "last_chat_action": action,
                "rejected_reason": reject_reason,
            },
        )
        response = RescueResponseResult(
            surfaced=True,
            reply_text="收到，我先把這個 rescue 提案關掉。之後如果你想重新開補回方案，再直接跟我說。",
            recommended_days=None,
            daily_kcal_adjustment=None,
            overshoot_kcal=None,
            quick_actions=[],
            top_option=proposal.options[0] if proposal.options else None,
            backup_options=[],
            ui_hints={"mode": "rescue_proposal_closed"},
        )
        return RescueChatSurfaceResult(
            surfaced=True,
            response=response,
            proposal_container_id=proposal.proposal_container_id,
            proposal_status=str(decision["proposal_status"]),
            writeback=None,
        )

    response = apply_rescue_plan_action(proposal=proposal, action=action)
    return RescueChatSurfaceResult(
        surfaced=response.surfaced,
        response=response,
        proposal_container_id=proposal.proposal_container_id,
        proposal_status=proposal.proposal_status,
        writeback=None,
    )
