from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _memory_do_not_save_policy_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="memory_do_not_save_policy_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4A_MEMORY_MODEL_SPEC.md#8a-what-not-to-save",
            "runtime_filter_installed": False,
            "policy_enforced_in_runtime_now": False,
            "product_capability_filter": _product_capability_filter(),
            "forbidden_memory_classes": _forbidden_memory_classes(),
            "candidate_allowed_classes": _candidate_allowed_classes(),
            "privacy_retention_policy": _privacy_retention_policy(),
            "deterministic_boundary": _deterministic_boundary(),
            "review_examples": _review_examples(),
        },
    )


def _product_capability_filter() -> dict[str, bool]:
    return {
        "must_have_declared_future_consumer": True,
        "must_improve_product_capability": True,
        "consumerless_context_rejected": True,
        "annoyance_or_creepiness_risk_blocks_promotion": True,
    }


def _forbidden_memory_classes() -> list[dict[str, str]]:
    return [
        {
            "class_id": "raw_secret_or_credential",
            "reason": "Never store production secrets, credentials, or private tokens as memory.",
        },
        {
            "class_id": "one_off_low_signal_food_event",
            "reason": "A single incidental meal should not become a preference or profile claim.",
        },
        {
            "class_id": "transient_mood_without_user_request",
            "reason": "Temporary emotional wording is not product-useful memory unless the user asks to remember it.",
        },
        {
            "class_id": "unsupported_medical_inference",
            "reason": "Do not infer medical conditions or clinical facts from diet/body traces.",
        },
        {
            "class_id": "cross_user_or_cross_project_context",
            "reason": "Memory scope must not leak between users, projects, or workspaces.",
        },
        {
            "class_id": "raw_full_transcript",
            "reason": "Long transcript is a retrieval source, not a durable user memory object.",
        },
        {
            "class_id": "unapproved_response_style_profile",
            "reason": "L4A marks conversation style profile as future extension, not active runtime truth.",
        },
    ]


def _candidate_allowed_classes() -> list[dict[str, str]]:
    return [
        {
            "class_id": "explicit_user_preference",
            "required_guard": "source_ref_plus_human_review_before_runtime_use",
        },
        {
            "class_id": "confirmed_negative_preference",
            "required_guard": "explicit_negative_signal_or_repeated_corrections",
        },
        {
            "class_id": "temporary_preference_with_expiry",
            "required_guard": "valid_from_valid_until_and_expiry_review",
        },
        {
            "class_id": "repeated_behavior_pattern",
            "required_guard": "evidence_count_and_freshness_threshold",
        },
        {
            "class_id": "correction_tendency_with_source_refs",
            "required_guard": "correction_lineage_and_consumer_value",
        },
        {
            "class_id": "proactive_suppression_signal",
            "required_guard": "cooldown_snooze_dismiss_trace_and_no_send_policy",
        },
    ]


def _privacy_retention_policy() -> dict[str, bool]:
    return {
        "source_scope_required": True,
        "retention_posture_required": True,
        "privacy_class_required": True,
        "source_refs_required": True,
        "chat_review_correction_path_required_later": True,
        "delete_or_suppress_path_required_later": True,
        "raw_trace_retained_only_as_audit_source": True,
    }


def _deterministic_boundary() -> dict[str, bool]:
    return {
        "may_reject_unqualified_candidate": True,
        "may_require_more_evidence": True,
        "may_create_semantic_user_profile": False,
        "may_override_human_confirmation": False,
    }


def _review_examples() -> list[dict[str, Any]]:
    return [
        {
            "example_id": "single_ramen_once",
            "save_allowed": False,
            "reason": "one_off_low_signal_food_event",
        },
        {
            "example_id": "dont_recommend_cilantro",
            "save_allowed": True,
            "reason": "candidate_confirmed_negative_preference_after_review",
        },
        {
            "example_id": "low_oil_this_week",
            "save_allowed": True,
            "reason": "temporary_preference_requires_expiry",
        },
        {
            "example_id": "user_says_normal_bento_and_later_corrects_portion",
            "save_allowed": True,
            "reason": "user_language_or_correction_tendency_candidate",
        },
    ]


__all__ = ["_memory_do_not_save_policy_shadow_artifact"]
