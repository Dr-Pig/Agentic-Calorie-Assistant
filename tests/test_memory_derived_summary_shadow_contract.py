from __future__ import annotations

from app.memory.application.derived_summary_shadow_contract import (
    build_memory_derived_summary_shadow_contract_artifact,
)


REQUIRED_CASES = [
    "preference_profile_from_committed_history_only",
    "golden_order_materialized_not_promoted",
    "suppression_ignored_signal_only",
    "manager_context_injection_blocked",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_memory_shadow_contract_is_read_only_derived_summary_only() -> None:
    artifact = build_memory_derived_summary_shadow_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_memory_derived_summary_shadow_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/memory"
    assert artifact["consumer"] == "future memory/recommendation/proactive activation slices"
    assert artifact["retirement_trigger"] == "approved durable_memory_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["derived_summary_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["memory_provider_used"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["llm_extraction_invoked"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_preference_profile_summary_is_derived_from_committed_history_only() -> None:
    case = _by_id(build_memory_derived_summary_shadow_contract_artifact())[
        "preference_profile_from_committed_history_only"
    ]

    assert case["source_kind"] == "derived_read_model"
    assert case["is_durable_memory_truth"] is False
    assert case["top_item"] == "chicken bento"
    assert case["top_store"] == "Corner Bento"
    assert case["source_events"] == ["meal-1", "meal-2"]
    assert case["durable_memory_written"] is False


def test_golden_order_is_materialized_view_not_memory_promotion() -> None:
    case = _by_id(build_memory_derived_summary_shadow_contract_artifact())[
        "golden_order_materialized_not_promoted"
    ]

    assert case["source_kind"] == "derived_read_model"
    assert case["golden_order_count"] == 1
    assert case["golden_order_source"] == "canonical_history_materialized_view"
    assert case["confirmed_memory_promoted"] is False
    assert case["llm_extraction_invoked"] is False


def test_suppression_summary_counts_ignored_signals_without_durable_suppression() -> None:
    case = _by_id(build_memory_derived_summary_shadow_contract_artifact())[
        "suppression_ignored_signal_only"
    ]

    assert case["source_kind"] == "derived_read_model"
    assert case["suppression_trigger_type"] == "meal_reminder"
    assert case["suppression_count"] == 1
    assert case["dismissed_current_instance_counted"] is False
    assert case["confirmed_memory_promoted"] is False


def test_manager_context_injection_is_blocked_until_activation() -> None:
    case = _by_id(build_memory_derived_summary_shadow_contract_artifact())[
        "manager_context_injection_blocked"
    ]

    assert case["manager_context_injected"] is False
    assert case["manager_context_packet_schema_changed"] is False
    assert case["recommendation_served"] is False
    assert case["proactive_sent"] is False


def test_memory_shadow_validator_rejects_runtime_or_memory_write_drift() -> None:
    from app.memory.application import derived_summary_shadow_contract as module

    artifact = build_memory_derived_summary_shadow_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "durable_memory_written": True,
        "manager_context_injected": True,
        "confirmed_memory_promoted": True,
    }

    blockers = module._validate_cases(cases)

    assert "preference_profile_from_committed_history_only.durable_memory_written" in blockers
    assert "preference_profile_from_committed_history_only.manager_context_injected" in blockers
    assert "preference_profile_from_committed_history_only.confirmed_memory_promoted" in blockers
