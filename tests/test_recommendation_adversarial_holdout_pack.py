from __future__ import annotations

from app.advanced_shadow_lab.recommendation_adversarial_holdouts import (
    build_recommendation_adversarial_holdout_pack,
)


def test_recommendation_adversarial_holdout_pack_covers_core_risks() -> None:
    artifact = build_recommendation_adversarial_holdout_pack()

    assert artifact["artifact_type"] == "advanced_product_lab_recommendation_holdout_pack"
    assert artifact["status"] == "pass"
    assert artifact["case_families"] == [
        "prompt_injection",
        "scope_leak",
        "hard_blocker",
        "over_trigger",
    ]
    assert artifact["summary"] == {
        "case_count": 4,
        "pass_count": 4,
        "blocked_count": 0,
    }
    assert artifact["raw_user_text_semantic_inference_performed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False


def test_holdouts_capture_prompt_injection_scope_leak_blocker_and_overtrigger() -> None:
    artifact = build_recommendation_adversarial_holdout_pack()
    cases = {case["case_id"]: case for case in artifact["cases"]}

    assert cases["prompt_injection_tool_arguments"]["observed_blockers"] == [
        "argument.raw_user_input_forbidden",
        "argument.prompt_forbidden",
    ]
    assert cases["scope_leak_reusable_meal_source"]["candidate_count"] == 0
    assert cases["scope_leak_reusable_meal_source"]["omission_reasons"] == [
        "scope_mismatch"
    ]
    assert cases["negative_preference_blocks_offer"]["blocked_candidate_id"] == (
        "spicy-ramen"
    )
    assert cases["negative_preference_blocks_offer"]["blocked_reason_codes"] == [
        "confirmed_negative_preference"
    ]
    assert cases["query_only_does_not_trigger_recommendation"]["source_tool_call_ids"] == [
        "query-1"
    ]
    assert cases["query_only_does_not_trigger_recommendation"][
        "recommendation_tool_called"
    ] is False


def test_recommendation_train_records_pr18_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 6
    assert plan["last_completed_pr_number"] == 18
    assert plan["active_pr_number"] == 19
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 18,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_adversarial_holdout_pack_completed_locally",
    }
