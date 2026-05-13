from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_stress_pr_train.yaml"
)
REVIEW_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_mechanism_review.yaml"
)
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def test_context_engineering_stress_pr_train_records_dynamic_slice_plan() -> None:
    plan = _load(PLAN_PATH)

    assert plan["artifact_type"] == "advanced_product_lab_context_engineering_stress_pr_train"
    assert plan["status"] == "planned"
    assert plan["planned_slice_count_likely"] == 16
    assert plan["dynamic_remaining_slice_count"] == 5
    assert plan["slice_count_range"] == {
        "optimistic": 14,
        "likely": 16,
        "conservative": 19,
    }
    assert len(plan["slice_train"]) == 16
    assert plan["slice_train"][0]["slice_id"] == "main_to_lab_sync_and_contract_drift_audit"
    assert plan["slice_train"][-1]["slice_id"] == "decision_pack_and_proactive_entry_gate"

    assert plan["last_completed_slice_number"] == 11
    assert plan["last_merge_evidence"]["completed_slices"][-1] == {
        "slice_number": 11,
        "slice_id": "fixture_planner_provider_for_ce_stress",
        "result": "fixture_planner_provider_completed",
        "artifact": "app/advanced_shadow_lab/context_engineering_fixture_planner_provider.py",
        "dynamic_remaining_slice_count_after": 5,
    }


def test_context_engineering_stress_pr_train_keeps_main_alignment_and_lab_activation_separate() -> None:
    plan = _load(PLAN_PATH)

    assert plan["branch_strategy"]["target_branch"] == "codex/advanced-product-lab"
    assert plan["branch_strategy"]["merge_back_to_main_posture"] == "dormant_until_activation_pr"
    assert plan["branch_strategy"]["main_to_lab_sync_required_before_runtime_slices"] is True
    assert plan["required_artifact_flags"]["lab_enabled"] is True
    assert plan["required_artifact_flags"]["mainline_activation_enabled"] is False
    assert plan["required_artifact_flags"]["production_scheduler_delivery_allowed"] is False
    assert plan["required_artifact_flags"]["canonical_product_mutation_allowed_on_main"] is False


def test_mechanism_review_challenges_pending_meal_intent_without_promoting_memory_or_canonical_truth() -> None:
    review = _load(REVIEW_PATH)

    assert review["artifact_type"] == "advanced_product_lab_context_engineering_mechanism_review"
    assert review["status"] == "active"
    assert review["overall_verdict"] == "skeleton_direction_sound_but_not_product_complete"

    pending = review["pending_meal_intent_assessment"]
    assert pending["recommended_option"] == "first_class_short_term_context_state"
    assert pending["rejected_options"]["long_term_memory_record"]["reason"] == (
        "wrong_lifespan_and_wrong_truth_owner"
    )
    assert pending["rejected_options"]["canonical_meal_thread_draft"]["reason"] == (
        "too_mutation_like_before_user_confirms_consumption"
    )
    assert pending["required_next_capabilities"] == [
        "store_lifecycle",
        "meal_window_policy",
        "context_pack_injection",
        "intake_handoff_on_confirmation",
        "dismiss_without_negative_memory",
        "expiry_and_followup_trace",
    ]


def test_mechanism_review_records_decision_ownership_boundaries() -> None:
    review = _load(REVIEW_PATH)
    boundary = review["llm_deterministic_boundary"]

    assert boundary["truth_owner"] == "hybrid"
    assert "classify_turn_and_plan_capabilities" in boundary["llm_role"]
    assert "enforce_mutation_legality" in boundary["deterministic_role"]
    assert "raw_user_text_keyword_route" in boundary["do_not_use_as_semantic_truth"]
    assert review["manager_style_gap_assessment"]["current_skeleton_gap"] == (
        "scripted_fixture_semantics_exist_before_live_planner_tool_selection_stress"
    )


def test_new_context_engineering_artifacts_are_indexed() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "advanced_product_lab_context_engineering_golden_set.yaml" in doc_index
    assert "advanced_product_lab_context_engineering_stress_pr_train.yaml" in doc_index
    assert "advanced_product_lab_context_engineering_mechanism_review.yaml" in doc_index
