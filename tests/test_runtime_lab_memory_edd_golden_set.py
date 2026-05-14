from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"
LAB_INDEX_PATH = ROOT / "docs" / "quality" / "ADVANCED_PRODUCT_LAB_INDEX.md"


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
    "source_lookup",
    "shared_feedback_event",
}


def test_runtime_lab_memory_edd_suite_loads_required_cases_and_splits() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    artifact = load_runtime_lab_memory_edd_suite()

    assert artifact["artifact_type"] == "runtime_lab_memory_edd_golden_set"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "MemoryRuntimeArchitecture"
    assert artifact["consumer"] == "runtime_lab_memory_slices"
    assert artifact["artifact_classification"] == "merge_safe"
    assert artifact["retirement_trigger"] == "approved_durable_memory_activation_plan"
    assert artifact["runtime_connected"] is False
    assert artifact["lab_isolated"] is True
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["case_count"] == 23
    assert set(artifact["case_types"]) == REQUIRED_CASE_TYPES
    assert artifact["split_counts"] == {
        "fixture": 17,
        "holdout": 3,
        "negative": 3,
    }
    assert artifact["suite_contract"]["required_scope_keys"] == [
        "user_id",
        "workspace_id",
        "project_id",
        "surface",
        "run_id",
    ]
    assert artifact["suite_contract"]["forbidden_capabilities"] == [
        "provider_call",
        "memory_store_write",
        "extraction_pipeline_activation",
        "manager_context_packet_injection",
        "scheduler_delivery",
        "canonical_mutation",
    ]


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
        "source_lookup_boundary",
        "feedback_event_projection",
    }
    assert rubric["promotion_legality"]["truth_owner"] == "deterministic_validator"
    assert rubric["retrieval_precision"]["grader_type"] == "hybrid_trace_plus_human_calibrated"
    assert rubric["no_canonical_mutation"]["blocking"] is True
    for item in rubric.values():
        assert item["grader_type"]
        assert item["truth_owner"]
        assert isinstance(item["blocking"], bool)
        assert item["pass_rule"]
    assert artifact["live_tests"] == {
        "stage_a_synthetic_runtime_traces": "deferred_to_PR3",
        "stage_b_dogfood_replay_traces": "deferred_to_PR4",
        "stage_c_env_gated_live_manager_diagnostic": "deferred_to_PR3",
        "stage_d_paired_lab_injection": "deferred_to_PR8",
        "stage_e_grokfast_extraction_diagnostic": "milestone_required",
        "stage_f_memory_tool_lookup_diagnostic": "milestone_required",
        "stage_g_recommendation_with_blockers": "milestone_required",
        "stage_h_proactive_feedback_projection": "milestone_required",
        "stage_i_integrated_e2e_lab_loop": "milestone_required",
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
        assert case["trace_fields"]["source_refs"]


def test_runtime_lab_memory_edd_indexed_as_conditional_guidance_only() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    lab_index = LAB_INDEX_PATH.read_text(encoding="utf-8-sig")
    active_bootstrap = doc_index[
        doc_index.index("## Active Bootstrap") : doc_index.index("## Active Truth Rules")
    ]

    assert "ADVANCED_PRODUCT_LAB_INDEX.md" in doc_index
    assert "runtime_lab_memory_edd_golden_set.yaml" in lab_index
    assert "runtime_lab_memory_edd_golden_set.yaml" not in active_bootstrap


def test_runtime_lab_memory_edd_projection_adds_reviewed_dogfood_cases_only() -> None:
    from app.memory.application.runtime_lab_candidate_extraction import (
        build_candidate_extraction_artifact_from_edd_suite,
    )
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        build_reviewed_dogfood_edd_suite_projection,
        load_runtime_lab_memory_edd_suite,
    )

    suite = load_runtime_lab_memory_edd_suite()
    review = build_memory_dogfood_replay_review_artifact([_reviewed_dogfood_record()])

    projection = build_reviewed_dogfood_edd_suite_projection(suite, review)

    assert projection["artifact_type"] == "runtime_lab_memory_edd_suite_projection"
    assert projection["status"] == "pass"
    assert projection["base_case_count"] == 23
    assert projection["reviewed_dogfood_case_count"] == 1
    assert projection["case_count"] == 24
    assert projection["split_counts"] == {
        "fixture": 17,
        "holdout": 4,
        "negative": 3,
    }
    assert projection["canonical_golden_set_mutated"] is False
    assert projection["reviewed_cases_promoted_to_canonical"] is False
    assert projection["durable_product_memory_written"] is False
    assert projection["manager_context_packet_changed"] is False
    assert projection["non_claims"] == [
        "not_product_activation_evidence",
        "not_private_self_use_approval",
        "not_canonical_golden_set_mutation",
    ]

    extraction = build_candidate_extraction_artifact_from_edd_suite(projection)
    assert extraction["candidate_count"] == 19
    assert extraction["rejection_count"] == 5


def test_runtime_lab_memory_edd_projection_blocks_missing_truth_refs() -> None:
    from app.memory.application.runtime_lab_dogfood_replay import (
        build_memory_dogfood_replay_review_artifact,
    )
    from app.memory.application.runtime_lab_memory_edd import (
        build_reviewed_dogfood_edd_suite_projection,
        load_runtime_lab_memory_edd_suite,
    )

    suite = load_runtime_lab_memory_edd_suite()
    suite["golden_set_policy"] = dict(suite["golden_set_policy"])
    suite["golden_set_policy"]["product_truth_source"] = []
    review = build_memory_dogfood_replay_review_artifact([_reviewed_dogfood_record()])

    projection = build_reviewed_dogfood_edd_suite_projection(suite, review)

    assert projection["status"] == "blocked"
    assert projection["case_count"] == 23
    assert "missing_product_truth_source_refs" in projection["blockers"]
    assert projection["canonical_golden_set_mutated"] is False


def test_runtime_lab_memory_edd_blocks_missing_contract_ownership() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    suite_path = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"
    text = suite_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "artifact_classification: merge_safe",
        "artifact_classification: diagnostic_only",
    ).replace(
        "retirement_trigger: approved_durable_memory_activation_plan",
        "retirement_trigger: ''",
    )
    temp_path = ROOT / ".pytest_tmp_local" / "bad_memory_edd_contract.yaml"
    temp_path.parent.mkdir(exist_ok=True)
    temp_path.write_text(mutated, encoding="utf-8")

    artifact = load_runtime_lab_memory_edd_suite(temp_path)

    assert artifact["status"] == "fail"
    assert "artifact_classification_not_merge_safe" in artifact["blockers"]
    assert "retirement_trigger_missing_or_unexpected" in artifact["blockers"]


def test_runtime_lab_memory_edd_blocks_missing_case_source_refs() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        load_runtime_lab_memory_edd_suite,
    )

    suite_path = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"
    text = suite_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "source_refs:\n        - message:event-explicit-preference-001",
        "source_refs: []",
        1,
    )
    temp_path = ROOT / ".pytest_tmp_local" / "bad_memory_edd_refs.yaml"
    temp_path.parent.mkdir(exist_ok=True)
    temp_path.write_text(mutated, encoding="utf-8")

    artifact = load_runtime_lab_memory_edd_suite(temp_path)

    assert artifact["status"] == "fail"
    assert (
        "explicit_preference_confirm_candidate.missing_source_refs"
        in artifact["blockers"]
    )


def test_runtime_lab_memory_edd_projection_blocks_unpassed_dogfood_review() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        build_reviewed_dogfood_edd_suite_projection,
        load_runtime_lab_memory_edd_suite,
    )

    suite = load_runtime_lab_memory_edd_suite()
    review = {
        "artifact_type": "runtime_lab_memory_dogfood_replay_review",
        "status": "blocked",
        "reviewed_case_proposals": [],
        "blockers": ["rt-lab-dogfood-keyword.raw_keyword_semantic_oracle_blocked"],
    }

    projection = build_reviewed_dogfood_edd_suite_projection(suite, review)

    assert projection["status"] == "blocked"
    assert projection["reviewed_dogfood_case_count"] == 0
    assert projection["blockers"] == [
        "dogfood_review_not_pass",
        "rt-lab-dogfood-keyword.raw_keyword_semantic_oracle_blocked",
    ]


def test_runtime_lab_memory_edd_projection_rejects_malformed_review_proposals() -> None:
    from app.memory.application.runtime_lab_memory_edd import (
        build_reviewed_dogfood_edd_suite_projection,
        load_runtime_lab_memory_edd_suite,
    )

    suite = load_runtime_lab_memory_edd_suite()
    proposal = dict(suite["cases"][0])
    proposal["source"] = "dogfood_replay"
    proposal["trace_fields"] = {"manager_decision_field": "memory_candidate_requested"}
    proposal.pop("expected_runtime_effects")
    review = {
        "artifact_type": "runtime_lab_memory_dogfood_replay_review",
        "status": "pass",
        "reviewed_case_proposals": [proposal],
    }

    projection = build_reviewed_dogfood_edd_suite_projection(suite, review)

    assert projection["status"] == "blocked"
    assert projection["case_count"] == 23
    assert projection["blockers"] == [
        "duplicate_case_id:explicit_preference_confirm_candidate",
        "explicit_preference_confirm_candidate.missing_source_refs",
        "explicit_preference_confirm_candidate.runtime_effects",
    ]


def _reviewed_dogfood_record() -> dict:
    request_id = "rt-lab-dogfood-suite-001"
    return {
        "trace": {
            "request_id": request_id,
            "trace_meta": {
                "request_id": request_id,
                "user_id": "user-a",
                "bundle": "intake_execution",
                "local_date": "2026-05-09",
            },
            "memory_lab_scope": {
                "workspace_id": "workspace-a",
                "project_id": "advanced-memory-runtime-lab",
                "surface": "manager_runtime_lab",
                "run_id": "suite-projection-run",
            },
            "request": {"user_id": "user-a", "text": "reviewed dogfood trace"},
            "manager_final_decision": {"workflow_effect": "commit_meal_log"},
            "memory_lab_candidate_signal": {
                "candidate_type": "preference",
                "manager_decision_field": "memory_candidate_requested",
                "source_refs": ["message:dogfood-suite-001"],
                "review_status": "pending",
                "promotion_allowed_now": False,
                "human_review_required": True,
                "reason_codes": ["explicit_user_preference"],
            },
        },
        "review": {
            "reviewer_id": "fixture-human-reviewer",
            "case_type": "explicit_preference",
            "split": "holdout",
            "expected_outcome": "candidate",
            "expected_candidate_type": "preference",
            "semantic_oracle_source": "product_rule_and_trace_fields",
            "raw_keyword_route_allowed": False,
            "source_ref_confirmation": True,
        },
    }
