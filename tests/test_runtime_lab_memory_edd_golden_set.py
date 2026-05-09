from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


REQUIRED_CASE_TYPES = {
    "explicit_preference",
    "negative_preference",
    "temporary_preference",
    "repeated_pattern",
    "golden_order",
    "correction_not_memory",
    "suppression",
    "stale_conflict",
    "scope_leak",
    "prompt_injection_attempt",
}


def test_runtime_lab_memory_edd_suite_loads_required_cases_and_splits() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    artifact = load_runtime_lab_memory_edd_suite()

    assert artifact["artifact_type"] == "runtime_lab_memory_edd_golden_set"
    assert artifact["status"] == "pass"
    assert artifact["runtime_connected"] is False
    assert artifact["lab_isolated"] is True
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["case_count"] == 10
    assert set(artifact["case_types"]) == REQUIRED_CASE_TYPES
    assert artifact["split_counts"] == {
        "fixture": 6,
        "holdout": 2,
        "negative": 2,
    }


def test_runtime_lab_memory_edd_rubric_is_decision_complete_without_live_claims() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    artifact = load_runtime_lab_memory_edd_suite()
    rubric = {item["dimension_id"]: item for item in artifact["rubric"]}

    assert set(rubric) == {
        "extraction",
        "promotion_legality",
        "retrieval_precision",
        "omission",
        "no_canonical_mutation",
        "scope_isolation",
        "secret_redaction",
    }
    assert rubric["promotion_legality"]["truth_owner"] == "deterministic_validator"
    assert rubric["retrieval_precision"]["grader_type"] == "hybrid_trace_plus_human_calibrated"
    assert rubric["no_canonical_mutation"]["blocking"] is True
    assert artifact["live_tests"] == {
        "stage_a_synthetic_runtime_traces": "deferred_to_PR3",
        "stage_b_dogfood_replay_traces": "deferred_to_PR4",
        "stage_c_env_gated_live_manager_diagnostic": "deferred_to_PR3",
        "stage_d_paired_lab_injection": "deferred_to_PR8",
    }
    assert "not_runtime_activation_evidence" in artifact["non_claims"]


def test_runtime_lab_memory_edd_cases_do_not_encode_raw_keyword_semantic_oracles() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    artifact = load_runtime_lab_memory_edd_suite()

    for case in artifact["cases"]:
        oracle = case["oracle"]
        assert oracle["semantic_oracle_source"] == "product_rule_and_trace_fields"
        assert oracle["raw_keyword_route_allowed"] is False
        assert "raw_input_keyword" not in oracle
        assert case["expected_runtime_effects"] == {
            "runtime_connected": False,
            "user_facing_behavior_changed": False,
            "canonical_mutation_changed": False,
            "durable_product_memory_written": False,
            "manager_context_packet_changed": False,
        }


def test_runtime_lab_memory_edd_indexed_as_conditional_guidance_only() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    active_bootstrap = doc_index[
        doc_index.index("## Active Bootstrap") : doc_index.index("## Active Truth Rules")
    ]

    assert "runtime-lab memory EDD golden set" in doc_index
    assert "runtime_lab_memory_edd_golden_set.yaml" in doc_index
    assert "runtime_lab_memory_edd_golden_set.yaml" not in active_bootstrap
