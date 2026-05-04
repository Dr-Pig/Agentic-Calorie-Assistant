from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.artifact_consumer_catalog import (
    ARTIFACT_CONSUMER_CATALOG,
)
from app.memory.application.long_term_context_shadow.utils import (
    _artifact_non_runtime_truth_reason,
    _artifact_promotion_path,
    _artifact_risk_if_wrong,
    _consumer_use_hints,
    _json_safe,
)

SHADOW_NON_CLAIM_FLAGS: dict[str, bool] = {
    "shadow_mode": True,
    "real_runtime_effect": False,
    "dogfood_db_mutated": False,
    "durable_memory_written": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "body_plan_mutated": False,
    "day_budget_mutated": False,
    "meal_thread_mutated": False,
    "product_readiness_claimed": False,
    "private_self_use_approved": False,
}

DOGFOOD_EXPORT_SECTIONS: tuple[str, ...] = (
    "meal_logs",
    "body_observations",
    "budget_summaries",
    "calibration_diagnostics",
    "language_observations",
    "intake_estimation_events",
    "app_usage_events",
    "interaction_events",
    "negative_preference_observations",
    "temporary_preference_observations",
    "conversation_history_summaries",
    "trace_metadata",
    "candidate_pool",
    "menu_scan_context",
    "review_actions",
)

CHAT_TRACE_SECTION_ALIASES: tuple[str, ...] = (
    "chat_trace_metadata",
    "chat_traces",
    "conversation_trace_metadata",
)


def _base_artifact(
    *,
    artifact_type: str,
    fixture: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    generated_at = str(fixture.get("generated_at_utc") or "1970-01-01T00:00:00+00:00")
    contract = artifact_review_contract(artifact_type)
    payload = {
        "artifact_schema_version": "1.0",
        "artifact_type": artifact_type,
        "status": "generated",
        "generated_at_utc": generated_at,
        "claim_scope": "long_term_context_shadow_lab",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "input_reader": fixture.get("_input_reader")
        or {
            "source_shape": "top_level_fixture",
            "fixture_input_used": True,
            "real_dogfood_export_used": False,
            "real_dogfood_export_claim_ignored": False,
            "normalized_sections": [],
            "supported_sections": list(DOGFOOD_EXPORT_SECTIONS)
            + ["chat_trace_metadata"],
            "direct_db_access_used": False,
            "live_provider_called": False,
        },
        **SHADOW_NON_CLAIM_FLAGS,
        **contract,
        **extra,
    }
    payload["runtime_effect_allowed"] = False
    return _json_safe(payload)


def artifact_review_contract(artifact_type: str) -> dict[str, Any]:
    consumers = ARTIFACT_CONSUMER_CATALOG.get(
        artifact_type,
        ["human_review", "architecture_governance"],
    )
    return {
        "intended_consumers": consumers,
        "consumer_use_hints": _consumer_use_hints(consumers),
        "risk_if_wrong": _artifact_risk_if_wrong(artifact_type),
        "promotion_path": _artifact_promotion_path(artifact_type),
        "runtime_effect_allowed": False,
        "why_this_is_not_runtime_truth": _artifact_non_runtime_truth_reason(
            artifact_type
        ),
    }
