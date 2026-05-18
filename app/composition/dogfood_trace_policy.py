from __future__ import annotations

from typing import Any, Literal

DogfoodTraceStatus = Literal[
    "raw_trace",
    "review_candidate",
    "human_labeled",
    "golden_candidate",
    "canonical_eval_case",
]
UnsupportedIntentFamily = Literal[
    "rescue",
    "recommendation",
    "meal_planning",
    "proactive_reminder",
    "long_term_memory",
]
UserCorrectionType = Literal[
    "portion_correction",
    "kcal_override",
    "item_addition",
    "item_removal",
    "component_reclassification",
    "drink_modifier_correction",
]
ManagerMode = Literal["fixture", "grokfast_diagnostic", "kimi"]

_STABLE_BEHAVIOR_KEY = "stable_" + "expected_" + "behavior"
_CANONICAL_EVAL_REQUIREMENTS = (
    "human_approval",
    "product_semantic_source",
    _STABLE_BEHAVIOR_KEY,
    "regression_test_or_eval_registration",
)
_DETERMINISTIC_REVIEW_FLAGS = {
    "manager_decision_parse_failed",
    "invalid_final_action_combo",
    "runtime_rejected_manager_decision",
    "no_accepted_food_packet",
    "evidence_confidence_low",
    "source_conflict",
    "fallback_used_for_common_food",
    "user_replied_to_pending_followup_but_no_pending_draft_found",
    "pending_draft_expired_or_unresolved",
    "target_attachment_ambiguous",
    "user_correction",
    "portion_correction",
    "kcal_override",
    "item_addition",
    "item_removal",
    "unsupported_intent",
    "same_truth_failed",
    "read_model_mismatch",
    "frontend_error",
}
_UNSUPPORTED_NOTICE_ONLY = {"proactive_reminder", "long_term_memory", "meal_planning"}

CHAT_TURN_ROUTE_CONTRACT = {
    "current_route": "/estimate",
    "semantic_role": "accurate_intake_chat_turn_entrypoint",
    "accepts": ["raw_user_text", "user_session_date_context"],
    "manager_may_return": [
        "estimate_and_commit",
        "ask_followup",
        "correction_applied",
        "removal_applied",
        "query_answer",
        "target_update",
        "unsupported_answer_only",
    ],
    "route_name_is_truth_owner": False,
    "route_name_warning": "legacy route name is narrower than chat-turn semantic role",
}


def _clean_list(values: Any) -> list[str]:
    return [str(value) for value in values or [] if str(value or "").strip()]


def _review_proposers(
    auto_flags: list[str],
    reviewer_agent_suggestion: dict[str, Any] | None,
) -> list[str]:
    proposers: list[str] = []
    if any(flag in _DETERMINISTIC_REVIEW_FLAGS for flag in auto_flags):
        proposers.append("deterministic_rules")
    if reviewer_agent_suggestion:
        proposers.append("optional_reviewer_agent")
    return proposers


def _status_for_record(
    *,
    auto_flags: list[str],
    reviewer_agent_suggestion: dict[str, Any] | None,
    human_label: dict[str, Any] | None,
    promotion: dict[str, Any] | None,
) -> DogfoodTraceStatus:
    if promotion and promotion.get("canonical_eval_case") is True and human_label:
        return "canonical_eval_case"
    if promotion and promotion.get("golden_candidate") is True:
        return "golden_candidate"
    if human_label:
        return "human_labeled"
    if _review_proposers(auto_flags, reviewer_agent_suggestion):
        return "review_candidate"
    return "raw_trace"


def build_dogfood_review_record(
    *,
    trace_id: str,
    raw_trace: dict[str, Any],
    auto_flags: list[str] | tuple[str, ...] | None = None,
    reviewer_agent_suggestion: dict[str, Any] | None = None,
    human_label: dict[str, Any] | None = None,
    promotion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flags = _clean_list(auto_flags)
    reviewer_payload = dict(reviewer_agent_suggestion or {})
    human_payload = dict(human_label or {})
    promotion_payload = dict(promotion or {})
    proposers = _review_proposers(flags, reviewer_payload if reviewer_payload else None)
    status = _status_for_record(
        auto_flags=flags,
        reviewer_agent_suggestion=reviewer_payload if reviewer_payload else None,
        human_label=human_payload if human_payload else None,
        promotion=promotion_payload if promotion_payload else None,
    )
    return {
        "trace_id": trace_id,
        "status": status,
        "raw_trace": dict(raw_trace),
        "raw_trace_is_truth": False,
        "auto_flags": flags,
        "review_candidate": {
            "proposed_by": proposers,
            "approved_by_required": False,
            "reviewer_agent_can_approve": False,
        },
        "reviewer_agent_suggestion": reviewer_payload or None,
        "human_labeled": {
            "required_for_canonical_eval": True,
            "label": human_payload or None,
        },
        "golden_candidate": {
            "proposed": bool(promotion_payload.get("golden_candidate")),
            "status": "candidate_only_until_human_approval",
        },
        "promotion": promotion_payload or None,
    }


def validate_canonical_eval_promotion(record: dict[str, Any]) -> dict[str, Any]:
    human_label = dict(dict(record.get("human_labeled") or {}).get("label") or {})
    promotion = dict(record.get("promotion") or {})
    missing: list[str] = []
    if not human_label.get("approved_by"):
        missing.append("human_approval")
    if not promotion.get("product_semantic_source"):
        missing.append("product_semantic_source")
    if promotion.get(_STABLE_BEHAVIOR_KEY) is not True:
        missing.append(_STABLE_BEHAVIOR_KEY)
    if not promotion.get("regression_test_or_eval_registration"):
        missing.append("regression_test_or_eval_registration")
    missing = [item for item in _CANONICAL_EVAL_REQUIREMENTS if item in missing]
    return {"allowed": not missing, "missing": missing}


def build_unsupported_intent_policy(family: UnsupportedIntentFamily | str) -> dict[str, Any]:
    family_value = str(family)
    subtype = "unsupported_intent_notice" if family_value in _UNSUPPORTED_NOTICE_ONLY else "general_guidance"
    return {
        "final_action": "answer_only",
        "answer_only_subtype": subtype,
        "unsupported_intent_family": family_value,
        "mutation_allowed": False,
        "target_change_allowed": False,
        "product_capability_claimed": False,
        "trace_as_future_roadmap_signal": True,
        "forbidden_side_effects": [
            "create_meal_thread",
            "create_food_item",
            "update_daily_target",
            "create_pending_food_draft",
            "create_reminder",
            "create_meal_plan",
        ],
    }


def build_user_correction_feedback_event(
    *,
    trace_id: str,
    original_user_input: str,
    original_estimate: dict[str, Any],
    correction_text: str,
    correction_type: UserCorrectionType | str,
    final_accepted_estimate: dict[str, Any] | None,
    likely_failure_family: str,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "event_type": "user_correction_feedback",
        "original_user_input": original_user_input,
        "original_estimate": dict(original_estimate),
        "correction_text": correction_text,
        "correction_type": str(correction_type),
        "final_accepted_estimate": dict(final_accepted_estimate or {}),
        "likely_failure_family": likely_failure_family,
        "review_status": "raw",
        "food_kb_truth_update_allowed": False,
        "canonical_eval_promotion_allowed": False,
    }


def build_session_date_policy(
    *,
    active_local_date: str,
    requested_date: str | None,
) -> dict[str, Any]:
    if requested_date is None:
        return {
            "active_local_date": active_local_date,
            "requested_date": None,
            "date_status": "ambiguous",
            "mutation_allowed": False,
            "required_behavior": "block_mutation_or_ask_clarification",
        }
    if requested_date == active_local_date:
        return {
            "active_local_date": active_local_date,
            "requested_date": requested_date,
            "date_status": "supported_current_active_date",
            "mutation_allowed": True,
            "required_behavior": "allow_current_active_date_flow",
        }
    return {
        "active_local_date": active_local_date,
        "requested_date": requested_date,
        "date_status": "limited_or_unsupported",
        "mutation_allowed": False,
        "required_behavior": "block_mutation_or_ask_clarification",
    }


def build_manager_mode_policy(
    *,
    manager_mode: ManagerMode | str,
    provider_profile: str | None = None,
    live_call_used: bool = False,
    model_id: str | None = None,
) -> dict[str, Any]:
    mode = str(manager_mode)
    trace_fields = {
        "manager_mode": mode,
        "provider_profile": provider_profile,
        "live_call_used": bool(live_call_used),
        "model_id": model_id,
    }
    if mode == "fixture":
        return {
            "manager_mode": mode,
            "default_for_deterministic_dogfood": True,
            "explicit_only": False,
            "readiness_claim_allowed": False,
            "trace_fields": trace_fields,
        }
    if mode == "grokfast_diagnostic":
        return {
            "manager_mode": mode,
            "default_for_deterministic_dogfood": False,
            "explicit_only": True,
            "readiness_claim_allowed": False,
            "active_runtime_default_allowed": False,
            "trace_fields": trace_fields,
        }
    return {
        "manager_mode": mode,
        "default_for_deterministic_dogfood": False,
        "explicit_only": True,
        "deferred_until_target_model_validation": True,
        "readiness_claim_allowed": False,
        "active_runtime_default_allowed": False,
        "trace_fields": trace_fields,
    }


def build_dogfood_turn_trace_policy(manager_decision: Any) -> dict[str, Any]:
    decision = dict(manager_decision) if isinstance(manager_decision, dict) else {}
    unsupported_family = str(decision.get("unsupported_intent_family") or "").strip()
    manager_mode = str(decision.get("manager_mode") or "fixture").strip() or "fixture"
    provider_profile = decision.get("provider_profile")
    model_id = decision.get("model_id")
    return {
        "lifecycle_status": "raw_trace",
        "raw_trace_is_truth": False,
        "review_candidate_can_be_auto_proposed": True,
        "canonical_eval_requires_human_approval": True,
        "unsupported_intent_policy": (
            build_unsupported_intent_policy(unsupported_family) if unsupported_family else None
        ),
        "manager_mode_policy": build_manager_mode_policy(
            manager_mode=manager_mode,
            provider_profile=str(provider_profile) if provider_profile is not None else None,
            live_call_used=bool(decision.get("live_call_used") is True),
            model_id=str(model_id) if model_id is not None else None,
        ),
    }


__all__ = [
    "CHAT_TURN_ROUTE_CONTRACT", "build_dogfood_turn_trace_policy",
    "build_dogfood_review_record", "build_manager_mode_policy",
    "build_session_date_policy",
    "build_unsupported_intent_policy",
    "build_user_correction_feedback_event",
    "validate_canonical_eval_promotion",
]
