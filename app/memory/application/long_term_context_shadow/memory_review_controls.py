from __future__ import annotations


USER_EQUIVALENT_ACTION_TYPES = (
    "confirm_candidate_semantics",
    "do_not_save_candidate",
    "forget_memory_record",
)

_EXCLUSION_REASON_BY_ACTION_TYPE = {
    "do_not_save_candidate": "do_not_save_by_user",
    "forget_memory_record": "forgotten_by_user_shadow_tombstone",
}


def review_control_semantics() -> dict[str, object]:
    return {
        "semantic_owner": "human_or_user_review_action",
        "deterministic_role": "validate_scope_apply_audit_tombstone_and_exclusion",
        "llm_role": "none",
        "deterministic_semantic_inference_allowed": False,
        "user_equivalent_actions": sorted(USER_EQUIVALENT_ACTION_TYPES),
        "forget_semantics": "shadow_tombstone_retains_audit_no_durable_delete",
        "mainline_activation_allowed": False,
    }


def is_user_equivalent_action(action_type: str) -> bool:
    return action_type in USER_EQUIVALENT_ACTION_TYPES


def excluded_reason(
    record_state: str,
    action_type: str,
    reason_by_state: dict[str, str],
) -> str:
    return _EXCLUSION_REASON_BY_ACTION_TYPE.get(
        action_type,
        reason_by_state[record_state],
    )


def record_review_flags(action_type: str) -> dict[str, object]:
    return {
        "confirmation_status": (
            "user_confirmed_candidate_semantics"
            if action_type == "confirm_candidate_semantics"
            else None
        ),
        "do_not_save_requested": action_type == "do_not_save_candidate",
        "forget_requested": action_type == "forget_memory_record",
        "forget_semantics": (
            "shadow_tombstone_retains_audit"
            if action_type == "forget_memory_record"
            else None
        ),
        "durable_delete_performed": False,
    }


__all__ = [
    "USER_EQUIVALENT_ACTION_TYPES",
    "excluded_reason",
    "is_user_equivalent_action",
    "record_review_flags",
    "review_control_semantics",
]
