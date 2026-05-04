from __future__ import annotations

from typing import Any

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

ARTIFACT_CONSUMER_CATALOG: dict[str, list[str]] = {
    "artifact_registry_manifest": ["human_review", "architecture_governance"],
    "long_term_memory_candidate_review": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
        "chat_context",
    ],
    "context_value_review_queue": ["human_review", "architecture_governance"],
    "context_signal_quality_scorecard": [
        "human_review",
        "architecture_governance",
    ],
    "candidate_extraction_engine_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "context_value_scoring_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "shadow_replay_evaluators": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "review_queue_reducer": ["human_review", "architecture_governance"],
    "context_pack_token_pressure_shadow_eval": [
        "context_packing_review",
        "architecture_governance",
    ],
    "proactive_no_send_simulation": ["proactive", "human_review"],
    "recommendation_shadow_eval": ["recommendation", "human_review"],
    "rescue_shadow_candidates": ["rescue_later", "human_review"],
    "memory_review_action_shadow_result": ["human_review", "memory_governance"],
    "memory_promotion_demotion_shadow_eval": ["human_review", "memory_governance"],
    "semantic_pattern_extraction_shadow_plan": [
        "recommendation",
        "nightly_insight",
        "confirmed_memory_candidate_review",
    ],
    "conversation_recall_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "conversation_recall_tool_shadow_plan": [
        "chat_context",
        "future_manager_context_retrieval",
    ],
    "conversation_recall_retrieval_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "entity_normalization_shadow_plan": [
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "context_quality_contradiction_review_queue": [
        "human_review",
        "architecture_governance",
    ],
    "capability_scenario_fixture_pack": [
        "human_review",
        "architecture_governance",
    ],
    "pr_review_autopilot_closeout": ["human_review", "delivery_governance"],
    "long_term_context_pack_shadow_eval": [
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
    ],
    "product_capability_context_map": [
        "architecture_governance",
        "human_review",
    ],
    "external_memory_framework_research_review": [
        "architecture_governance",
        "human_review",
    ],
    "local_memory_framework_review": ["architecture_governance", "human_review"],
    "local_memory_framework_deep_review": [
        "architecture_governance",
        "human_review",
    ],
}


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


def build_artifact_registry_manifest(
    fixture_payload: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    from app.memory.application.long_term_context_shadow.fixture_reader import (
        _normalize_dogfood_export_payload,
    )

    fixture = (
        dict(fixture_payload)
        if "_input_reader" in fixture_payload
        else _normalize_dogfood_export_payload(fixture_payload)
    )
    return _artifact_registry_manifest_artifact(
        fixture,
        {
            artifact_key: artifact
            for artifact_key, artifact in artifacts.items()
            if artifact_key != "artifact_registry_manifest"
        },
    )


def _artifact_registry_manifest_artifact(
    fixture: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries = [
        _artifact_registry_entry(
            artifact_key="artifact_registry_manifest",
            artifact_type="artifact_registry_manifest",
            artifact=artifact_review_contract("artifact_registry_manifest"),
        )
    ]
    entries.extend(
        _artifact_registry_entry(
            artifact_key=artifact_key,
            artifact_type=str(artifact.get("artifact_type") or artifact_key),
            artifact=artifact,
        )
        for artifact_key, artifact in artifacts.items()
    )
    artifacts_without_consumers = [
        entry["artifact_key"] for entry in entries if not entry["intended_consumers"]
    ]
    pseudo_runtime_truth_risks = [
        entry["artifact_key"]
        for entry in entries
        if entry["runtime_effect_allowed"] or not entry["why_this_is_not_runtime_truth"]
    ]
    return _base_artifact(
        artifact_type="artifact_registry_manifest",
        fixture=fixture,
        extra={
            "manifest_scope": "batch_1_shadow_lab_artifact_registry",
            "artifact_count": len(entries),
            "artifact_registry_entries": entries,
            "artifacts_without_consumers": artifacts_without_consumers,
            "pseudo_runtime_truth_risks": pseudo_runtime_truth_risks,
            "all_artifacts_have_future_consumers": not artifacts_without_consumers,
            "all_artifacts_block_runtime_truth": not pseudo_runtime_truth_risks,
        },
    )


def _artifact_registry_entry(
    *,
    artifact_key: str,
    artifact_type: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_key": artifact_key,
        "artifact_type": artifact_type,
        "intended_consumers": list(artifact.get("intended_consumers") or []),
        "consumer_use_hints": dict(artifact.get("consumer_use_hints") or {}),
        "risk_if_wrong": str(artifact.get("risk_if_wrong") or ""),
        "promotion_path": str(artifact.get("promotion_path") or ""),
        "runtime_effect_allowed": bool(artifact.get("runtime_effect_allowed") is True),
        "why_this_is_not_runtime_truth": str(
            artifact.get("why_this_is_not_runtime_truth") or ""
        ),
        "manager_context_injection_allowed": False,
        "durable_memory_write_allowed": False,
        "future_consumer_declared": bool(artifact.get("intended_consumers")),
    }
