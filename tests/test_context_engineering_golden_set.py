from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_case_loader import (
    GOLDEN_SET_PATH,
    golden_set_case_ids,
    load_context_engineering_golden_set,
)


def test_context_engineering_golden_set_exists_and_loads() -> None:
    artifact = load_context_engineering_golden_set()

    assert GOLDEN_SET_PATH.exists()
    assert artifact["artifact_type"] == "advanced_product_lab_context_engineering_golden_set"
    assert artifact["version"] == 2
    assert artifact["status"] == "active"
    assert len(artifact["cases"]) == 30


def test_context_engineering_golden_set_schema_covers_overlap_cases() -> None:
    artifact = load_context_engineering_golden_set()

    required = set(artifact["case_schema"]["required_fields"])
    assert {
        "case_id",
        "coverage_scope",
        "user_turn",
        "expected_primary_workflow",
        "expected_capabilities",
        "forbidden_capabilities",
        "expected_ordering_constraints",
        "mutation_posture",
        "expected_trace",
        "accepted_variants",
        "evaluator",
    }.issubset(required)

    case_ids = golden_set_case_ids()
    assert case_ids == [f"ce-stress-{index:03d}" for index in range(1, 31)]


def test_context_engineering_golden_set_records_fixture_negative_and_live_split_targets() -> None:
    artifact = load_context_engineering_golden_set()
    split_counts = {
        split: sum(1 for item in artifact["cases"] if item["split"] == split)
        for split in artifact["split_targets"]
    }

    assert artifact["split_targets"] == {
        "fixture": 18,
        "negative_holdout": 8,
        "live_diagnostic_seed": 4,
    }
    assert split_counts == artifact["split_targets"]


def test_context_engineering_golden_set_covers_product_capability_categories() -> None:
    artifact = load_context_engineering_golden_set()
    category_counts = {
        category: sum(1 for item in artifact["cases"] if item["category"] == category)
        for category in artifact["category_targets"]
    }

    assert artifact["category_targets"] == {
        "multi_capability": 8,
        "intake_query_bridge": 5,
        "recommendation_memory": 5,
        "pending_meal_intent": 4,
        "rescue": 4,
        "overtrigger_holdout": 4,
    }
    assert category_counts == artifact["category_targets"]


def test_context_engineering_golden_set_locks_pending_intent_and_rescue_policy() -> None:
    artifact = load_context_engineering_golden_set()
    decisions = artifact["global_decisions"]

    assert decisions["pending_meal_intent"]["state_category"] == "short_term_context"
    assert decisions["pending_meal_intent"]["ttl_hours"] == 6
    assert decisions["pending_meal_intent"]["canonical_write_authorized"] is False
    assert decisions["pending_meal_intent"]["quiet_hours_policy"] == (
        "chat_thread_message_only_no_push"
    )
    assert decisions["rescue"]["unprompted_overshoot_threshold_pct"] == 25
    assert decisions["rescue"]["explicit_conditional_request_can_run_same_turn"] is True
    assert decisions["memory"]["confirmed_negative_priority"] == (
        "block_or_downrank_before_positive_boost"
    )


def test_context_engineering_golden_set_avoids_keyword_oracle_and_preserves_manager_truth() -> None:
    artifact = load_context_engineering_golden_set()
    policy = artifact["evaluation_policy"]

    assert policy["no_raw_keyword_semantic_oracle"] is True
    assert policy["eval_assets_do_not_define_product_truth"] is True
    assert policy["semantic_decision_owner"] == "manager_llm_structured_output"
    assert "tool_selection" in policy["trace_surfaces"]
    assert "argument_precision" in policy["trace_surfaces"]
    assert "final_response_boundary" in policy["trace_surfaces"]


def test_context_engineering_golden_set_includes_key_user_calibrated_cases() -> None:
    artifact = load_context_engineering_golden_set()
    by_id = {item["case_id"]: item for item in artifact["cases"]}

    assert by_id["ce-stress-001"]["expected_capabilities"] == [
        "intake",
        "query",
        "rescue",
        "recommendation",
    ]
    assert by_id["ce-stress-001"]["expected_ordering_constraints"] == [
        "intake_before_query",
        "query_before_rescue",
        "rescue_before_recommendation",
    ]
    assert by_id["ce-stress-006"]["expected_capabilities"] == [
        "recommendation",
        "pending_meal_intent",
    ]
    assert by_id["ce-stress-019"]["expected_trace"]["pending_meal_intent"][
        "expires_in_hours"
    ] == 6
    assert by_id["ce-stress-024"]["expected_trace"]["proactive_delivery"] == "blocked"
