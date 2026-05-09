from __future__ import annotations

from typing import Any, Mapping

from app.runtime.application.proactive_no_send_nudge_candidate import (
    build_no_send_nudge_candidate,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_nudge_bridge"
)
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
    "manager_context_packet_changed": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "mutation_changed": False,
}


def build_no_send_nudge_candidate_bridge(
    *,
    recommendation_prompt_review: Mapping[str, Any] | None = None,
    rescue_nudge_review: Mapping[str, Any] | None = None,
    user_control_models: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = _candidate_attempts(
        recommendation_prompt_review=recommendation_prompt_review,
        rescue_nudge_review=rescue_nudge_review,
        user_control_models=user_control_models,
    )
    blockers = _bridge_blockers(candidates)
    passed_candidates = [] if blockers else candidates
    simulation_inputs = _simulation_inputs(passed_candidates)
    return {
        "artifact_type": "proactive_no_send_nudge_candidate_bridge",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_proactive_no_send_shadow_simulation",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "candidate_count": len(passed_candidates),
        "candidates": _public_candidates(passed_candidates),
        "simulation_input_metadata": _simulation_input_metadata(simulation_inputs),
        "simulation_inputs": simulation_inputs,
        "blockers": blockers,
        "non_claims": [
            "not_notification",
            "not_scheduler_activation",
            "not_live_delivery",
            "not_user_facing_proactive",
            "not_candidate_or_proposal_payload",
        ],
        **dict(FALSE_FLAGS),
    }


def _candidate_attempts(
    *,
    recommendation_prompt_review: Mapping[str, Any] | None,
    rescue_nudge_review: Mapping[str, Any] | None,
    user_control_models: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if recommendation_prompt_review is not None:
        candidates.append(
            build_no_send_nudge_candidate(
                trigger_type="recommendation_prompt",
                candidate_source=recommendation_prompt_review,
                user_control_model=user_control_models.get("recommendation_prompt", {}),
                wake_source="app_open",
            )
        )
    if rescue_nudge_review is not None:
        candidates.append(
            build_no_send_nudge_candidate(
                trigger_type="rescue_nudge",
                candidate_source=rescue_nudge_review,
                user_control_model=user_control_models.get("rescue_nudge", {}),
                wake_source="manual_shadow_review",
            )
        )
    return candidates


def _bridge_blockers(candidates: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        trigger_type = str(candidate.get("trigger_type") or "unknown")
        if candidate.get("status") != "pass":
            blockers.extend(
                f"{trigger_type}.{blocker}"
                for blocker in list(candidate.get("blockers") or [])
            )
        for flag, value in FALSE_FLAGS.items():
            if value is False and candidate.get(flag) is True:
                blockers.append(f"{trigger_type}.{flag}")
    return blockers


def _simulation_inputs(candidates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []
    for candidate in candidates:
        trigger_type = str(candidate.get("trigger_type") or "")
        if trigger_type == "recommendation_prompt":
            inputs.append(
                {
                    "trigger_type": trigger_type,
                    "data_sufficiency_status": "higher",
                    "user_benefit_strength": "strong",
                    "lower_frequency_ready": True,
                    "delivery_surface": "app_open",
                    "recommendation_prompt_review": _review_stub(candidate),
                    "wake_source": "app_open",
                    "user_relevant_reason": str(
                        candidate.get("next_signal_required") or ""
                    ),
                }
            )
        elif trigger_type == "rescue_nudge":
            inputs.append(
                {
                    "trigger_type": trigger_type,
                    "data_sufficiency_status": "higher",
                    "user_benefit_strength": "strong",
                    "delivery_surface": "app_open",
                    "rescue_nudge_review": _review_stub(candidate),
                    "wake_source": "manual_shadow_review",
                    "user_relevant_reason": str(
                        candidate.get("next_signal_required") or ""
                    ),
                }
            )
    return inputs


def _review_stub(candidate: Mapping[str, Any]) -> dict[str, Any]:
    trigger_type = str(candidate.get("trigger_type") or "")
    if trigger_type == "recommendation_prompt":
        return {
            "source_report_used": True,
            "status": "candidate_for_human_review",
            "recommendation_pool_decision": "primary_plus_backup",
            "prompt_posture": "invitation_only",
            "actual_candidates_included": False,
            "candidate_ids_exposed": False,
            **dict(FALSE_FLAGS),
        }
    return {
        "source_projection_used": True,
        "status": "context_available",
        "prompt_posture": "later_only_review_context",
        **dict(FALSE_FLAGS),
    }


def _public_candidates(candidates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "artifact_type": str(candidate.get("artifact_type") or ""),
            "status": str(candidate.get("status") or ""),
            "trigger_type": str(candidate.get("trigger_type") or ""),
            "candidate_kind": str(candidate.get("candidate_kind") or ""),
            "dismiss_reason_choices": list(candidate.get("dismiss_reason_choices") or []),
            "snooze_window": dict(candidate.get("snooze_window") or {}),
            "undo_scope": str(candidate.get("undo_scope") or ""),
            "next_signal_required": str(candidate.get("next_signal_required") or ""),
            **dict(FALSE_FLAGS),
        }
        for candidate in candidates
    ]


def _simulation_input_metadata(
    inputs: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "trigger_type": str(item.get("trigger_type") or ""),
            "wake_source": str(item.get("wake_source") or ""),
            "delivery_surface": str(item.get("delivery_surface") or ""),
            "candidate_kind": "recommendation_prompt_review"
            if item.get("trigger_type") == "recommendation_prompt"
            else "rescue_nudge_review",
            "has_required_user_controls": True,
        }
        for item in inputs
    ]


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_no_send_nudge_candidate_bridge",
]
