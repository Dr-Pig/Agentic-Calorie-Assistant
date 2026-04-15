from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy.orm import Session

from ..models import User
from .canonical_commit_bridge import apply_proposal_decision_skeleton
from .open_proposals_read_model import build_open_rescue_proposals_view
from .rescue_overlay import apply_overlay_days_payload
from .rescue_response import RescuePlanAction, RescueResponseResult, apply_rescue_plan_action, build_rescue_response_result

RescueChatMode = Literal["proactive", "reactive_explicit_rescue_request"]
ReasonHint = Literal["too_aggressive", "bad_timing", "not_now", "unclear"]
DEFER_REMINDER_HOURS = 12


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


def _now() -> datetime:
    return datetime.now()


def _classify_reason_hint(reason: str | None) -> ReasonHint:
    text = (reason or "").strip().lower()
    if not text:
        return "unclear"
    aggressive_keywords = ("太激進", "太硬", "太餓", "太累", "aggressive", "hard", "strict")
    timing_keywords = ("沒空", "時間", "行程", "忙", "timing", "schedule", "travel")
    not_now_keywords = ("這次不要", "先不要", "現在不要", "not now", "later", "skip")
    if any(keyword in text for keyword in aggressive_keywords):
        return "too_aggressive"
    if any(keyword in text for keyword in timing_keywords):
        return "bad_timing"
    if any(keyword in text for keyword in not_now_keywords):
        return "not_now"
    return "unclear"


def _reason_bridge_payload(*, reason: str | None, source: str) -> dict[str, Any]:
    normalized = (reason or "").strip()
    return {
        "raw_reason_text": normalized,
        "reason_hint": _classify_reason_hint(normalized),
        "reason_source": source,
        "captured_at": _now().isoformat(timespec="seconds"),
    }


def _parse_next_reminder_at(proposal: Any) -> datetime | None:
    value = proposal.metadata.get("next_reminder_at") if isinstance(proposal.metadata, dict) else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_reminder_due(proposal: Any) -> bool:
    next_reminder_at = _parse_next_reminder_at(proposal)
    if next_reminder_at is None:
        return True
    return next_reminder_at <= _now()


def build_rescue_chat_surface(
    db: Session,
    *,
    user_id: int,
    mode: RescueChatMode,
) -> RescueChatSurfaceResult:
    proposals = build_open_rescue_proposals_view(db, user_id=user_id)
    proposal = proposals[0] if proposals else None

    if proposal is not None and mode == "proactive" and proposal.proposal_status == "deferred_pending_reminder" and not _is_reminder_due(proposal):
        return RescueChatSurfaceResult(
            surfaced=False,
            response=RescueResponseResult(
                surfaced=False,
                reply_text="",
                recommended_days=None,
                daily_kcal_adjustment=None,
                overshoot_kcal=None,
                quick_actions=[],
                top_option=proposal.options[0] if proposal.options else None,
                backup_options=[],
                ui_hints={
                    "mode": "rescue_deferred_waiting",
                    "next_reminder_at": proposal.metadata.get("next_reminder_at"),
                    "proposal_status": proposal.proposal_status,
                },
            ),
            proposal_container_id=proposal.proposal_container_id,
            proposal_status=proposal.proposal_status,
            writeback=None,
        )

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
    reason: str | None = None,
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
            reply_text="好，這次我就照這個補回方案執行，之後會按這個節奏繼續。",
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

    if action == "defer_rescue_plan":
        reason_text = (reason or reject_reason or "").strip() or None
        now = _now()
        reminder_at = (now + timedelta(hours=DEFER_REMINDER_HOURS)).isoformat(timespec="seconds")
        metadata_patch: dict[str, Any] = {
            "last_chat_action": action,
            "deferred_at": now.isoformat(timespec="seconds"),
            "next_reminder_at": reminder_at,
            "pending_state": "proposal_pending",
        }
        if reason_text:
            metadata_patch["reason_bridge"] = _reason_bridge_payload(reason=reason_text, source="defer")
        decision = apply_proposal_decision_skeleton(
            db,
            proposal_container_id=proposal.proposal_container_id,
            decision="deferred_pending_reminder",
            metadata_patch=metadata_patch,
        )
        response = apply_rescue_plan_action(proposal=proposal, action=action)
        return RescueChatSurfaceResult(
            surfaced=True,
            response=RescueResponseResult(
                surfaced=response.surfaced,
                reply_text=response.reply_text,
                recommended_days=response.recommended_days,
                daily_kcal_adjustment=response.daily_kcal_adjustment,
                overshoot_kcal=response.overshoot_kcal,
                quick_actions=[],
                top_option=proposal.options[0] if proposal.options else None,
                backup_options=[],
                ui_hints={
                    **dict(response.ui_hints),
                    "next_reminder_at": reminder_at,
                    "proposal_status": str(decision["proposal_status"]),
                },
            ),
            proposal_container_id=proposal.proposal_container_id,
            proposal_status=str(decision["proposal_status"]),
            writeback=None,
        )

    if action == "reject_rescue_plan" and (reason or reject_reason):
        reason_text = (reason or reject_reason or "").strip()
        decision = apply_proposal_decision_skeleton(
            db,
            proposal_container_id=proposal.proposal_container_id,
            decision="rejected",
            metadata_patch={
                "last_chat_action": action,
                "rejected_reason": reason_text,
                "reason_bridge": _reason_bridge_payload(reason=reason_text, source="reject"),
            },
        )
        response = RescueResponseResult(
            surfaced=True,
            reply_text="好，這次 rescue 我先取消掉。之後你就照原本節奏走，這次的原因我會先記下來。",
            recommended_days=None,
            daily_kcal_adjustment=None,
            overshoot_kcal=None,
            quick_actions=[],
            top_option=proposal.options[0] if proposal.options else None,
            backup_options=[],
            ui_hints={"mode": "rescue_proposal_closed", "reason_bridge": decision["metadata"].get("reason_bridge")},
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
