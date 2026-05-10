from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "quality" / "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md"
CONTRACT_PATH = ROOT / "docs" / "quality" / "advanced_memory_mechanism_contract.yaml"
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _contract() -> dict[str, object]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_advanced_memory_spec_is_indexed_without_bootstrap_takeover() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    active_bootstrap = _section(doc_index, "## Active Bootstrap", "## Active Truth Rules")

    assert "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md" in doc_index
    assert "advanced_memory_mechanism_contract.yaml" in doc_index
    assert "advanced memory mechanism build order" in doc_index
    assert "ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md" not in active_bootstrap
    assert "advanced_memory_mechanism_contract.yaml" not in active_bootstrap


def test_contract_preserves_no_runtime_claim_boundary() -> None:
    contract = _contract()
    claim_scope = contract["claim_scope"]

    assert contract["current_mainline_unchanged"] is True
    assert contract["slice_mode"] == [
        "diagnostic_only",
        "offline_runtime",
        "shadow_foundation",
        "producer_honesty",
    ]

    for field in (
        "runtime_connected",
        "user_facing_behavior_changed",
        "runtime_truth_changed",
        "mutation_changed",
        "durable_memory_write_approved",
        "manager_context_injection_approved",
        "scheduler_activation_approved",
        "recommendation_serving_approved",
        "rescue_proposal_commit_approved",
        "proactive_send_approved",
        "product_readiness_claimed",
        "private_self_use_approved",
    ):
        assert claim_scope[field] is False


def test_memory_layers_and_promotion_rules_follow_canonical_specs() -> None:
    contract = _contract()
    layers = {layer["id"]: layer for layer in contract["memory_layers"]}
    rules = contract["promotion_rules"]

    assert set(layers) == {
        "typed_history",
        "statistical_pattern",
        "semantic_pattern",
        "confirmed_memory",
        "negative_preference",
        "temporary_preference",
        "golden_order",
        "archive",
        "interaction_preference_suppression",
    }
    assert layers["typed_history"]["truth_owner"] == "canonical_product_objects"
    assert layers["semantic_pattern"]["llm_live_extraction_allowed_now"] is False
    assert (
        layers["semantic_pattern"][
            "isolated_lab_live_candidate_generation_allowed_after_dormancy_gate"
        ]
        is True
    )
    assert layers["confirmed_memory"]["durable_write_allowed_now"] is False
    assert layers["golden_order"]["truth_owner"] == "canonical_history_materialized_view"
    assert layers["golden_order"]["promotion_result"] is False
    assert layers["negative_preference"]["confirmed_negative_auto_demote"] is False

    assert rules["same_store_item_pattern_min_repeats"] == 3
    assert rules["same_item_kind_pattern_min_repeats"] == 5
    assert rules["same_time_preference_min_repeats"] == 5
    assert rules["golden_order_min_repeats_in_30_days"] == 3
    assert rules["golden_order_recent_observation_max_days"] == 60
    assert rules["pattern_to_confirmed"] == {
        "min_reinforcement_count": 5,
        "min_confidence": 0.8,
        "min_consistency_days": 30,
        "requires_user_confirmation": True,
        "llm_may_complete_promotion": False,
    }


def test_consumer_dependency_order_keeps_memory_first_and_proactive_no_send_last() -> None:
    contract = _contract()
    boundaries = contract["consumer_boundaries"]

    assert contract["consumer_dependency_order"] == [
        "advanced_memory_shadow_foundation",
        "recommendation_shadow",
        "rescue_shadow",
        "proactive_no_send_shadow",
        "activation_planning",
    ]
    assert boundaries["recommendation_shadow"]["runtime_serving_allowed"] is False
    assert boundaries["recommendation_shadow"]["live_search_allowed"] is False
    assert boundaries["rescue_shadow"]["proposal_commit_allowed"] is False
    assert boundaries["rescue_shadow"]["budget_mutation_allowed"] is False
    assert boundaries["proactive_no_send_shadow"]["scheduler_activation_allowed"] is False
    assert boundaries["proactive_no_send_shadow"]["notification_send_allowed"] is False
    assert boundaries["proactive_no_send_shadow"]["trigger_persistence_allowed"] is False


def test_advanced_lab_memory_policy_records_latest_model_and_trace_decisions() -> None:
    contract = _contract()
    policy = contract["advanced_lab_execution_policy"]

    assert policy["current_first_slice"] == "advanced_runtime_lab_dormancy_contract"
    assert policy["current_first_slice_live_provider_calls_allowed"] is False
    assert policy["isolated_lab_semantic_candidate_generation_allowed_after_dormancy_gate"] is True
    assert policy["mainline_live_provider_semantic_extraction_allowed"] is False
    assert policy["provider_family"] == "builderspace"
    assert policy["diagnostic_live_model"] == "grok-4-fast"
    assert policy["target_reasoning_model"] == "kimi-k2.5"
    assert policy["kimi_live_calls_allowed_in_this_train"] is False
    assert policy["simulated_dogfood_allowed_until_real_traces_exist"] is True
    assert policy["real_dogfood_trace_required_for_promotion_claim"] is True
    assert policy["fooddb_expansion_allowed"] is False
    assert policy["fooddb_expansion_requires_real_self_use"] is True
    assert policy["proactive_surface"] == "chat_only"
    assert policy["mainline_activation_requires_separate_pr"] is True


def test_spec_forbids_runtime_first_overengineering() -> None:
    contract = _contract()
    spec = SPEC_PATH.read_text(encoding="utf-8-sig")

    assert "The first goal is not to create a memory service." in spec
    assert "Do Not Build Yet" in spec
    assert "durable memory service" in spec
    assert "database migrations for memory tables" in spec
    assert "ManagerContextPacket memory injection" in spec
    assert "scheduler activation" in spec
    assert "Advanced Runtime Lab Addendum" in spec
    assert "BuilderSpace `grok-4-fast` only" in spec
    assert "`kimi-k2.5` is the target reasoning-model profile" in spec
    assert "Proactive output is chat-only" in spec
    assert "FoodDB expansion waits for real self-use" in spec

    assert contract["forbidden_before_activation"] == [
        "durable_memory_service",
        "database_migration",
        "background_consolidation_worker",
        "live_provider_semantic_extraction",
        "vector_memory_index",
        "manager_context_packet_injection",
        "scheduler_activation",
        "notification_delivery",
        "app_open_recommendation_serving",
        "user_visible_memory_settings_surface",
        "cross_session_personalization",
    ]
    assert "not_runtime_activation_evidence" in contract["non_claims"]
