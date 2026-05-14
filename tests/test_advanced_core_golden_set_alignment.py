from __future__ import annotations


def test_advanced_core_alignment_report_covers_all_required_domains() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        build_advanced_core_golden_set_alignment_report,
    )

    report = build_advanced_core_golden_set_alignment_report()

    assert report["artifact_type"] == "advanced_core_golden_set_alignment_report"
    assert report["status"] == "pass"
    assert report["blockers"] == []
    assert report["mainline_activation_enabled"] is False
    assert report["raw_keyword_semantic_oracle_allowed"] is False
    assert report["existing_sets_policy"] == "audit_and_patch_gaps"
    assert report["product_surface_policy"]["primary_interaction_surface"] == "chat"
    assert "generic_inbox_as_primary_product_surface" in (
        report["product_surface_policy"]["forbidden_surface_semantics"]
    )
    assert "positive_capability_path" in (
        report["semantic_contract_width_policy"]["required_axes"]
    )
    assert "deterministic_raw_text_keyword_oracle" in (
        report["semantic_contract_width_policy"]["narrow_contract_signals"]
    )
    assert set(report["coverage_domains"]) == {
        "memory",
        "rescue",
        "recommendation",
        "proactive",
        "context_engineering",
        "reusable_meal",
        "cross_journey",
    }
    assert report["new_golden_sets"] == [
        "advanced_product_lab_recommendation_golden_set",
        "advanced_product_lab_proactive_golden_set",
        "advanced_product_lab_cross_journey_golden_set",
    ]


def test_recommendation_golden_set_locks_product_semantics_and_splits() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_recommendation_golden_set,
        validate_golden_set_contract,
    )

    artifact = load_recommendation_golden_set()
    validation = validate_golden_set_contract(artifact)

    assert validation["status"] == "pass"
    assert validation["blockers"] == []
    assert artifact["artifact_type"] == "advanced_product_lab_recommendation_golden_set"
    assert artifact["status"] == "active_alignment_contract"
    assert artifact["suite_contract"]["required_split_counts"] == {
        "fixture": 9,
        "negative_holdout": 3,
        "live_diagnostic_seed": 2,
    }
    assert set(artifact["suite_contract"]["required_case_types"]) == {
        "three_node_graph",
        "candidate_source",
        "hard_blocker",
        "soft_boost",
        "budget_gate",
        "offer_synthesis",
        "pending_meal_handoff",
        "feedback_projection",
        "rescue_posture",
        "reusable_meal_golden_order",
        "scope_leak",
        "overtrigger",
        "live_planning_seed",
        "live_offer_seed",
    }


def test_proactive_golden_set_requires_send_skip_controls_and_silence() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_proactive_golden_set,
        validate_golden_set_contract,
    )

    artifact = load_proactive_golden_set()
    validation = validate_golden_set_contract(artifact)

    assert validation["status"] == "pass"
    assert validation["blockers"] == []
    assert artifact["artifact_type"] == "advanced_product_lab_proactive_golden_set"
    assert artifact["suite_contract"]["required_split_counts"] == {
        "fixture": 8,
        "negative_holdout": 4,
        "live_diagnostic_seed": 2,
    }
    assert set(artifact["suite_contract"]["required_case_types"]) == {
        "wake_trigger",
        "deterministic_gate",
        "llm_send_skip",
        "quiet_hours",
        "cooldown",
        "dismiss_snooze_reopen_modify",
        "chat_first_delivery",
        "stay_silent",
        "permission_posture",
        "copy_safety",
        "feedback_suppression",
        "scheduler_activation_wall",
        "live_send_skip_seed",
        "live_feedback_seed",
    }


def test_cross_journey_golden_set_validates_complete_ux_loops() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_cross_journey_golden_set,
        validate_golden_set_contract,
    )

    artifact = load_cross_journey_golden_set()
    validation = validate_golden_set_contract(artifact)

    assert validation["status"] == "pass"
    assert validation["blockers"] == []
    assert artifact["artifact_type"] == "advanced_product_lab_cross_journey_golden_set"
    assert artifact["suite_contract"]["required_split_counts"] == {
        "fixture": 6,
        "negative_holdout": 2,
    }
    case_types = {case["case_type"] for case in artifact["cases"]}
    assert {
        "recommendation_to_pending_meal_to_intake",
        "memory_blocker_to_recommendation",
        "rescue_to_recommendation_posture",
        "proactive_feedback_to_suppression",
        "reusable_meal_to_intake_confirmation",
        "proactive_meal_reminder_to_intake",
        "ambiguous_attachment_no_wrong_mutation",
        "prompt_injection_no_activation",
    } == case_types


def test_reusable_meal_golden_set_expands_beyond_four_case_seed() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_reusable_meal_alignment_golden_set,
        validate_golden_set_contract,
    )

    artifact = load_reusable_meal_alignment_golden_set()
    validation = validate_golden_set_contract(artifact)

    assert validation["status"] == "pass"
    assert validation["blockers"] == []
    assert artifact["artifact_type"] == "advanced_product_lab_reusable_meal_golden_set"
    assert artifact["suite_contract"]["required_split_counts"] == {
        "fixture": 8,
        "negative_holdout": 4,
    }
    assert set(artifact["suite_contract"]["required_case_types"]) == {
        "same_meal_recall",
        "anchored_repeat",
        "ingredient_drift",
        "low_repetition_candidate",
        "golden_order_materialization",
        "fooddb_fallback_personal_template",
        "intake_confirmation_handoff",
        "correction_review",
        "store_variant_false_match",
        "portion_variant_false_match",
        "ambiguous_same_as_before",
        "scope_leak",
    }


def test_all_new_golden_cases_have_product_trace_and_non_keyword_oracles() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_all_advanced_core_golden_sets,
    )

    for artifact in load_all_advanced_core_golden_sets():
        required_fields = set(artifact["case_schema"]["required_fields"])
        for case in artifact["cases"]:
            assert required_fields.issubset(case)
            assert case["oracle"]["semantic_oracle_source"] == (
                "product_rule_and_trace_fields"
            )
            assert case["oracle"]["raw_keyword_route_allowed"] is False
            assert case["product_truth"]
            assert case["expected_trace_fields"]
            assert "canonical_mutation" in case["mutation_posture"]
            assert "mainline_activation" in case["mutation_posture"]


def test_advanced_core_golden_sets_declare_semantic_contract_width() -> None:
    from app.advanced_shadow_lab.advanced_core_golden_sets import (
        load_all_advanced_core_golden_sets,
        validate_golden_set_contract,
    )

    required_axes = {
        "positive_capability_path",
        "negative_or_blocking_path",
        "state_or_budget_constraint",
        "handoff_or_multi_capability",
        "ambiguity_or_scope_boundary",
        "overtrigger_false_positive",
    }

    for artifact in load_all_advanced_core_golden_sets():
        contract = artifact["suite_contract"]["semantic_contract_width"]
        validation = validate_golden_set_contract(artifact)

        assert validation["status"] == "pass"
        assert required_axes.issubset(contract["required_axes"])
        assert validation["semantic_contract_width"]["missing_required_axes"] == []
        assert validation["semantic_contract_width"]["unknown_axis_case_types"] == []


def test_doc_index_points_to_advanced_core_alignment_sets() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    doc_index = (root / "docs" / "DOC_INDEX.md").read_text(encoding="utf-8-sig")
    lab_index = (
        root / "docs" / "quality" / "ADVANCED_PRODUCT_LAB_INDEX.md"
    ).read_text(encoding="utf-8-sig")

    assert "ADVANCED_PRODUCT_LAB_INDEX.md" in doc_index
    assert "advanced_core_golden_set_coverage_matrix.yaml" in lab_index
    assert "advanced_product_lab_recommendation_golden_set.yaml" in lab_index
    assert "advanced_product_lab_proactive_golden_set.yaml" in lab_index
    assert "advanced_product_lab_cross_journey_golden_set.yaml" in lab_index
