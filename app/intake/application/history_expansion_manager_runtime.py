from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    HistoryExpansionRequest,
    HistoryExpansionResult,
    TransitionGuardResult,
)
from .attachment_resolver import resolve_attachment_decision
from .history_expansion_policy import build_history_expansion_request, build_history_expansion_result
from .history_expansion_candidates import (
    candidate_lexical_match,
    candidate_temporal_match,
    historical_candidates_from_state as _historical_candidates_from_state,
    recent_candidates_from_context as _recent_candidates_from_context,
    transcript_support_inventory as _transcript_support_inventory,
)
from .history_expansion_context_enrichment import enrich_current_turn_context
from .transition_guard import resolve_transition_guard

PHASE_A_EXPAND_HISTORY_TOOL = "phase_a_expand_history"
_VALID_REASONS = {"target_ambiguity", "correction_reference", "older_meal_reference", "unresolved_followup"}
_VALID_SCOPES = {"active_thread", "recent_meals", "committed_meals", "conversation_atomic_blocks"}


@dataclass(frozen=True)
class ManagerHistoryExpansionEligibility:
    eligible: bool
    reason: str
    request_reason: str | None = None
    request_scope: str | None = None


@dataclass(frozen=True)
class ManagerTriggeredHistoryExpansionResult:
    attempted: bool
    request: HistoryExpansionRequest | None
    result: HistoryExpansionResult | None
    atomic_blocks_status: str
    pre_attachment_decision: AttachmentDecision
    pre_transition_guard_result: TransitionGuardResult
    post_attachment_decision: AttachmentDecision
    post_transition_guard_result: TransitionGuardResult
    enriched_current_turn_context: CurrentTurnContextV1
    resolution_gain: bool
    selected_candidate_ids: tuple[str, ...] = ()
    ambiguity_detected: bool = False
    transcript_support_inventory: tuple[str, ...] = ()
    failure_family: str | None = None

    def tool_result(self) -> dict[str, Any]:
        return {
            "tool_name": PHASE_A_EXPAND_HISTORY_TOOL,
            "evidence": {
                "history_expansion_request": self.request.model_dump(mode="json") if self.request is not None else None,
                "history_expansion_result": self.result.model_dump(mode="json") if self.result is not None else None,
                "post_attachment_decision": self.post_attachment_decision.model_dump(mode="json"),
                "post_transition_guard_result": self.post_transition_guard_result.model_dump(mode="json"),
                "resolution_gain": self.resolution_gain,
            },
            "mutation_result": {},
            "provenance": {
                "phase_a_owner": "intake/application",
                "primary_truth": "structured_candidates",
                "transcript_support_inventory": list(self.transcript_support_inventory),
            },
            "confidence": "available" if self.attempted and self.result is not None else "none",
            "failure_family": self.failure_family,
        }

    def trace_payload(self) -> dict[str, Any]:
        summary = None
        if self.result is not None:
            summary = {
                "meal_candidate_count": len(self.result.meal_candidates),
                "atomic_block_count": len(self.result.atomic_blocks),
                "transcript_support_count": len(self.result.transcript_snippets),
            }
        return {
            "triggered": self.attempted,
            "reason": self.request.reason if self.request is not None else None,
            "scope": self.request.scope if self.request is not None else None,
            "request": self.request.model_dump(mode="json") if self.request is not None else None,
            "result_summary": summary,
            "atomic_blocks_status": self.atomic_blocks_status,
            "pre_decision": self.pre_attachment_decision.model_dump(mode="json"),
            "post_decision": self.post_attachment_decision.model_dump(mode="json"),
            "post_transition_guard_result": self.post_transition_guard_result.model_dump(mode="json"),
            "resolution_gain": self.resolution_gain,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "ambiguity_detected": self.ambiguity_detected,
            "transcript_support_inventory": list(self.transcript_support_inventory),
            "failure_family": self.failure_family,
        }


def manager_history_expansion_eligibility(
    *,
    current_turn_context: CurrentTurnContextV1,
    attachment_decision: AttachmentDecision,
    transition_guard_result: TransitionGuardResult,
) -> ManagerHistoryExpansionEligibility:
    event = current_turn_context.current_interaction_event
    if event.surface_mode != "chat_freeform":
        return ManagerHistoryExpansionEligibility(False, "explicit_ui_target")
    if event.target_object_id:
        return ManagerHistoryExpansionEligibility(False, "explicit_ui_target")
    if event.target_object_type == "proposal" or current_turn_context.open_workflow_type == "proposal":
        return ManagerHistoryExpansionEligibility(False, "non_meal_primary_route")
    if current_turn_context.pending_followup is not None and attachment_decision.target_object_id is not None:
        return ManagerHistoryExpansionEligibility(False, "resolved_pending_followup")
    if transition_guard_result.verdict == "pass":
        return ManagerHistoryExpansionEligibility(False, "already_safe_pass")
    unresolved_enough = attachment_decision.disposition == "answer_only" or transition_guard_result.verdict == "clarify_required"
    if not unresolved_enough:
        return ManagerHistoryExpansionEligibility(False, "not_unresolved")
    return ManagerHistoryExpansionEligibility(True, "manager_scope_required")


def _manager_requested_history_scope(arguments: dict[str, Any] | None) -> tuple[str, str] | None:
    payload = dict(arguments or {})
    reason = str(payload.get("reason") or payload.get("request_reason") or "").strip()
    scope = str(payload.get("scope") or payload.get("request_scope") or "").strip()
    if reason not in _VALID_REASONS or scope not in _VALID_SCOPES:
        return None
    return reason, scope


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        target_id = str(candidate.get("meal_thread_id") or "")
        if not target_id or target_id in seen:
            continue
        seen.add(target_id)
        deduped.append(candidate)
    return deduped


def _strong_candidates(
    candidates: list[dict[str, Any]],
    *,
    request: HistoryExpansionRequest,
    raw_user_input: str,
    current_turn_context: CurrentTurnContextV1,
    local_date: str | None,
) -> list[dict[str, Any]]:
    strong: list[dict[str, Any]] = []
    temporal_reason = "correction_reference" if request.reason == "target_ambiguity" else request.reason
    for candidate in candidates:
        if not candidate_temporal_match(
            candidate,
            reason=temporal_reason,
            raw_user_input=raw_user_input,
            local_date=local_date,
        ):
            continue
        if not candidate_lexical_match(
            candidate,
            raw_user_input=raw_user_input,
            current_turn_context=current_turn_context,
        ):
            continue
        strong.append(candidate)
    return strong


def activate_manager_triggered_history_expansion(
    *,
    current_turn_context: CurrentTurnContextV1,
    resolved_state: Any,
    pre_attachment_decision: AttachmentDecision | None = None,
    pre_transition_guard_result: TransitionGuardResult | None = None,
    manager_tool_arguments: dict[str, Any] | None = None,
) -> ManagerTriggeredHistoryExpansionResult:
    pre_attachment = pre_attachment_decision or resolve_attachment_decision(current_turn_context)
    pre_guard = pre_transition_guard_result or resolve_transition_guard(current_turn_context, pre_attachment)
    eligibility = manager_history_expansion_eligibility(
        current_turn_context=current_turn_context,
        attachment_decision=pre_attachment,
        transition_guard_result=pre_guard,
    )
    if not eligibility.eligible:
        return ManagerTriggeredHistoryExpansionResult(
            attempted=False,
            request=None,
            result=None,
            atomic_blocks_status="not_requested",
            pre_attachment_decision=pre_attachment,
            pre_transition_guard_result=pre_guard,
            post_attachment_decision=pre_attachment,
            post_transition_guard_result=pre_guard,
            enriched_current_turn_context=current_turn_context,
            resolution_gain=False,
            failure_family=f"phase_a_history_expansion_not_eligible:{eligibility.reason}",
        )
    requested_scope = _manager_requested_history_scope(manager_tool_arguments)
    if requested_scope is None:
        return ManagerTriggeredHistoryExpansionResult(
            attempted=False,
            request=None,
            result=None,
            atomic_blocks_status="not_requested",
            pre_attachment_decision=pre_attachment,
            pre_transition_guard_result=pre_guard,
            post_attachment_decision=pre_attachment,
            post_transition_guard_result=pre_guard,
            enriched_current_turn_context=current_turn_context,
            resolution_gain=False,
            failure_family="phase_a_history_expansion_manager_scope_missing",
        )

    request = build_history_expansion_request(
        reason=requested_scope[0],
        scope=requested_scope[1],
    )
    if request.scope == "recent_meals":
        candidate_pool = _recent_candidates_from_context(current_turn_context) + _historical_candidates_from_state(resolved_state)
    elif request.scope == "committed_meals":
        candidate_pool = _historical_candidates_from_state(resolved_state) + _recent_candidates_from_context(current_turn_context)
    elif request.scope == "active_thread":
        candidate_pool = _recent_candidates_from_context(current_turn_context)
    else:
        candidate_pool = _historical_candidates_from_state(resolved_state)
    candidates = _dedupe(candidate_pool)
    result = build_history_expansion_result(
        meal_candidates=[
            {
                "meal_thread_id": candidate["meal_thread_id"],
                "meal_version_id": candidate.get("meal_version_id"),
                "label": candidate.get("label") or "",
                "occurred_at": candidate.get("occurred_at"),
                "reason": candidate.get("source") or request.reason,
            }
            for candidate in candidates
        ],
        atomic_blocks=[],
        transcript_snippets=[],
    )
    strong = _strong_candidates(
        candidates,
        request=request,
        raw_user_input=current_turn_context.user_utterance,
        current_turn_context=current_turn_context,
        local_date=getattr(resolved_state, "local_date", None),
    )
    selected = strong[0] if len(strong) == 1 else None
    enriched = enrich_current_turn_context(
        current_turn_context=current_turn_context,
        selected_candidate=selected,
        activation_result=result,
        attachment_disposition_hint=(
            "attach_existing_thread" if request.reason in {"target_ambiguity", "unresolved_followup"}
            else "target_committed_thread"
        ),
    )
    post_attachment = resolve_attachment_decision(enriched)
    post_guard = resolve_transition_guard(enriched, post_attachment)
    resolution_gain = (
        pre_attachment.disposition == "answer_only"
        and post_attachment.disposition in {"attach_existing_thread", "target_committed_thread"}
    )
    return ManagerTriggeredHistoryExpansionResult(
        attempted=True,
        request=request,
        result=result,
        atomic_blocks_status="not_supplied",
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
        post_attachment_decision=post_attachment,
        post_transition_guard_result=post_guard,
        enriched_current_turn_context=enriched,
        resolution_gain=resolution_gain,
        selected_candidate_ids=(str(selected["meal_thread_id"]),) if selected is not None else (),
        ambiguity_detected=len(strong) > 1,
        transcript_support_inventory=_transcript_support_inventory(resolved_state),
    )


__all__ = [
    "ManagerHistoryExpansionEligibility",
    "ManagerTriggeredHistoryExpansionResult",
    "PHASE_A_EXPAND_HISTORY_TOOL",
    "activate_manager_triggered_history_expansion",
    "manager_history_expansion_eligibility",
]
