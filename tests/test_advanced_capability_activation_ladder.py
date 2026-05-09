from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "quality" / "advanced_capability_activation_ladder.yaml"
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _contract() -> dict[str, object]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_activation_ladder_is_indexed_without_bootstrap_takeover() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    active_bootstrap = _section(doc_index, "## Active Bootstrap", "## Active Truth Rules")

    assert "advanced_capability_activation_ladder.yaml" in doc_index
    assert "advanced capability activation ladder" in doc_index
    assert "advanced_capability_activation_ladder.yaml" not in active_bootstrap


def test_activation_ladder_preserves_stage_order_and_one_step_promotion() -> None:
    contract = _contract()

    assert contract["stage_order"] == [
        "contract",
        "fake",
        "deterministic",
        "live_diagnostic",
        "shadow",
        "read_only_runtime",
        "canary",
        "user_facing",
        "mutation_bearing",
    ]
    assert contract["promotion_rules"]["one_step_promotion_only"] is True
    assert contract["promotion_rules"]["human_review_required_for_stage_change"] is True
    assert contract["promotion_rules"]["evidence_must_name_holdouts"] is True
    assert contract["promotion_rules"]["rollback_or_kill_switch_required_from"] == [
        "canary",
        "user_facing",
        "mutation_bearing",
    ]


def test_all_advanced_capabilities_have_explicit_current_stage_and_dependencies() -> None:
    contract = _contract()
    capabilities = contract["capabilities"]

    assert set(capabilities) == {
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
    }
    assert capabilities["long_term_memory"]["current_stage"] == "shadow"
    assert capabilities["long_term_memory"]["next_allowed_stage"] == "read_only_runtime"
    assert capabilities["recommendation"]["depends_on"] == [
        "long_term_memory.read_only_runtime"
    ]
    assert capabilities["rescue"]["depends_on"] == [
        "long_term_memory.read_only_runtime"
    ]
    assert capabilities["proactive"]["depends_on"] == [
        "long_term_memory.read_only_runtime",
        "recommendation.read_only_runtime",
        "rescue.read_only_runtime",
    ]


def test_pre_promotion_no_go_flags_block_runtime_drift() -> None:
    contract = _contract()
    no_go = contract["pre_promotion_no_go_flags"]

    assert no_go["applies_to"] == "mainline_runtime_activation"
    for field in (
        "user_facing_behavior_changed",
        "canonical_mutation_changed",
        "durable_product_memory_written",
        "manager_context_packet_changed",
        "scheduler_activation_allowed",
        "notification_delivery_allowed",
        "recommendation_served",
        "rescue_proposal_committed",
        "route_or_api_activation_allowed",
        "product_db_migration_allowed",
        "live_provider_delivery_path_allowed",
    ):
        assert no_go[field] is False


def test_read_only_runtime_stage_allows_observation_without_authority() -> None:
    contract = _contract()
    read_only_runtime = contract["stage_requirements"]["read_only_runtime"]

    assert read_only_runtime["runtime_connected"] is True
    assert read_only_runtime["user_facing_behavior_changed"] is False
    assert read_only_runtime["canonical_mutation_changed"] is False
    assert read_only_runtime["manager_context_packet_changed"] is False
    assert read_only_runtime["durable_product_memory_written"] is False
    assert read_only_runtime["allowed_outputs"] == [
        "read_only_runtime_trace",
        "shadow_context_pack",
        "paired_baseline_comparison",
        "omission_trace",
    ]


def test_shadow_lab_can_build_complete_product_capability_without_mainline_activation() -> None:
    contract = _contract()
    lab_scope = contract["shadow_lab_scope"]

    assert lab_scope["goal"] == "complete_product_capability_and_ux_tasks"
    assert lab_scope["complete_product_capability_allowed"] is True
    assert lab_scope["lab_only_user_facing_surfaces_allowed"] is True
    assert lab_scope["lab_only_scheduler_simulation_allowed"] is True
    assert lab_scope["lab_only_isolated_mutation_ledger_allowed"] is True
    assert lab_scope["lab_only_durable_memory_store_allowed"] is True
    assert lab_scope["live_llm_diagnostic_allowed"] is True
    assert lab_scope["real_user_feedback_replay_allowed"] is True

    assert lab_scope["mainline_runtime_connection_allowed"] is False
    assert lab_scope["mainline_route_or_api_mount_allowed"] is False
    assert lab_scope["mainline_scheduler_delivery_allowed"] is False
    assert lab_scope["canonical_product_db_mutation_allowed"] is False
    assert lab_scope["manager_context_packet_production_change_allowed"] is False


def test_lab_complete_capability_requires_explicit_isolation_markers() -> None:
    contract = _contract()
    isolation = contract["shadow_lab_scope"]["required_isolation_markers"]

    assert isolation == {
        "lab_isolated": True,
        "mainline_runtime_connected": False,
        "user_facing_behavior_changed_in_mainline": False,
        "canonical_mutation_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
        "manager_context_packet_changed_in_mainline": False,
        "real_scheduler_or_notification_delivery": False,
        "lab_artifacts_may_include_complete_ux": True,
    }


def test_contract_records_best_practice_and_harness_minimization_boundaries() -> None:
    contract = _contract()
    best_practice = contract["best_practice_evidence"]
    harness = contract["harness_minimization"]

    assert best_practice["required"] is True
    assert {
        "openai_agents_guardrails",
        "openai_agent_evals",
        "openai_agents_sessions",
        "openai_agents_sandbox_memory",
    }.issubset(set(best_practice["sources_checked"]))
    assert "separate_session_history_from_durable_memory" in best_practice["adopted_guidance"]
    assert "trace_grading_before_repeatable_eval_runs" in best_practice["adopted_guidance"]
    assert "tool_guardrails_for_side_effectful_tool_calls" in best_practice["adopted_guidance"]

    assert harness == {
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "owner": "MemoryRuntimeArchitecture",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_product_runtime_activation_ledger_entries",
        "new_report_family_created": False,
    }
