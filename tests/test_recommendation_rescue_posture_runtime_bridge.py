from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_rescue_overlay_patches_recommendation_budget_before_candidate_guard() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-rescue-budget-turn"),
        fixture_inputs=_fixture_inputs_with_rescue_overlay(),
        lab_memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="lab-session-1",
            turn_id="recommendation-rescue-budget-turn",
        ),
    )

    bridge = artifact["product_lab_recommendation_rescue_posture_bridge_artifact"]
    recommendation = artifact["product_lab_recommendation_artifact"]
    filtered = {
        item["candidate_id"]: item["reason_codes"]
        for item in recommendation["retrieval_guard_scoring"]["filtered_candidates"]
    }

    assert bridge["status"] == "pass"
    assert bridge["rescue_posture_applied_to_recommendation"] is True
    assert bridge["source_handoff_artifact"]["rescue_posture_summary"][
        "remaining_budget_kcal_after_overlay"
    ] == 775
    assert recommendation["planning"]["candidate_spec"]["budget_posture"] == {
        "remaining_kcal": 775,
        "max_candidate_kcal": 775,
    }
    assert filtered["over-after-rescue"] == ["over_budget"]
    assert recommendation["canonical_product_mutation_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_offer_posture_reaches_rescue_without_consumption_claim() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-to-rescue-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    handoff = artifact["product_lab_rescue_artifact"]["recommendation_posture_handoff"]

    assert handoff["artifact_type"] == "rescue_recommendation_posture_handoff"
    assert handoff["status"] == "pass"
    assert handoff["recommendation_offer_served_to_lab"] is True
    assert handoff["selected_recommendation_candidate_id"] == "golden-1"
    assert handoff["offer_is_proposal_only"] is True
    assert handoff["must_not_count_offer_as_consumed"] is True
    assert handoff["pending_intake_confirmation_required"] is True
    assert handoff["meal_thread_mutated"] is False
    assert handoff["ledger_entry_created"] is False
    assert handoff["rescue_budget_view_mutated"] is False


def test_recommendation_train_records_pr14_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 10
    assert plan["last_completed_pr_number"] == 14
    assert plan["active_pr_number"] == 15
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 14,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_rescue_posture_handoff_completed_locally",
    }


def _fixture_inputs_with_rescue_overlay() -> dict[str, object]:
    return {
        **build_product_lab_fixture_inputs(),
        "recommendation_payload": _recommendation_payload_before_rescue(),
        "isolated_lab_rescue_commit_effect": _accepted_rescue_overlay_effect(),
    }


def _recommendation_payload_before_rescue() -> dict[str, object]:
    return {
        "current_budget_view": {"remaining_kcal": 1000},
        "negative_preference_summary": {"items": []},
        "open_rescue_context": {"accepted_conflict_patterns": []},
        "candidate_source_fixture": [
            _candidate("under-after-rescue", "grilled chicken rice", 700),
            _candidate("over-after-rescue", "large ramen", 850),
        ],
    }


def _candidate(candidate_id: str, title: str, max_kcal: int) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "source_type": "fooddb_fixture",
        "estimated_kcal": max_kcal,
        "estimated_kcal_range": {"min": max_kcal - 120, "max": max_kcal},
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "item_patterns": [title.replace(" ", "_")],
        "source_refs": [f"fixture:{candidate_id}"],
    }


def _accepted_rescue_overlay_effect() -> dict[str, object]:
    return {
        "artifact_type": "isolated_lab_rescue_commit_effect",
        "status": "pass",
        "refreshed_current_budget_view": {
            "user_id": "user-1",
            "local_date": "2026-05-13",
            "budget_kcal": 1800,
            "consumed_kcal": 600,
            "adjustment_kcal": 425,
            "remaining_kcal": 775,
        },
        "rescue_commit_effect": {
            "proposal_id": "rescue-proposal-1",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "effective_from": "2026-05-13Tafter_lunch",
            "effective_to": "2026-05-14",
        },
    }
