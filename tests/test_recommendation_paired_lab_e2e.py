from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.recommendation_paired_lab_e2e import (
    run_recommendation_paired_lab_e2e,
)


def test_recommendation_paired_lab_e2e_compares_baseline_and_enabled_path(
    tmp_path: Path,
) -> None:
    artifact = run_recommendation_paired_lab_e2e(
        turn=_turn(),
        fixture_inputs={
            **build_product_lab_fixture_inputs(),
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "reusable_meal_intake_signal": {
                "normalized_signature": "mom_fried_rice",
                "explicit_same_as_before": True,
                "repetition_count": 5,
            },
            "reusable_meal_entities": [_reusable_meal_entity()],
        },
        baseline_manager_script=_baseline_manager_script(),
        recommendation_manager_script=None,
        baseline_store=_seed_memory_store(tmp_path / "baseline"),
        recommendation_store=_seed_memory_store(tmp_path / "enabled"),
    )

    assert artifact["artifact_type"] == "advanced_product_lab_recommendation_paired_e2e"
    assert artifact["status"] == "pass"
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["baseline"]["manager_tool_names"] == [
        "query.run",
        "rescue.run",
    ]
    assert "recommendation.run" not in artifact["baseline"]["manager_tool_names"]
    assert artifact["recommendation_enabled"]["manager_tool_names"] == [
        "memory.search",
        "query.run",
        "reusable_meal.search",
        "recommendation.run",
        "rescue.run",
        "proactive.run",
    ]
    assert artifact["comparison"]["recommendation_tool_added"] is True
    assert artifact["comparison"]["pending_intake_handoff_added"] is True
    assert artifact["comparison"]["recommendation_candidate_id"]
    assert "ufe-fried-rice" in artifact["recommendation_enabled"][
        "recommendation_source_candidate_ids"
    ]
    assert artifact["comparison"]["lab_response_changed_by_recommendation_path"] is True
    assert artifact["comparison"]["canonical_mutation_changed"] is False
    assert artifact["comparison"]["mainline_activation_changed"] is False
    assert artifact["comparison"]["manager_context_packet_changed"] is False
    assert artifact["comparison"]["baseline_non_recommendation_path_valid"] is True
    assert artifact["comparison"]["recommendation_enabled_path_valid"] is True
    assert artifact["blockers"] == []


def test_recommendation_paired_lab_e2e_blocks_hidden_baseline_recommendation(
    tmp_path: Path,
) -> None:
    artifact = run_recommendation_paired_lab_e2e(
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        baseline_manager_script=None,
        recommendation_manager_script=None,
        baseline_store=_seed_memory_store(tmp_path / "baseline"),
        recommendation_store=_seed_memory_store(tmp_path / "enabled"),
    )

    assert artifact["status"] == "blocked"
    assert "baseline.recommendation_tool_present" in artifact["blockers"]
    assert artifact["comparison"]["baseline_non_recommendation_path_valid"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr20_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 4
    assert plan["last_completed_pr_number"] >= 20
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 21
    assert {
        "pr_number": 20,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_paired_lab_e2e_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _turn() -> dict[str, object]:
    return {
        "session_id": "lab-session-1",
        "turn_id": "paired-rec-turn",
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "multi_intent_recommendation_e2e",
    }


def _baseline_manager_script() -> list[dict[str, object]]:
    return [
        {
            "pass_id": "manager-pass-1",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "query-1",
                    "tool_name": "query.run",
                    "arguments": {},
                }
            ],
        },
        {
            "pass_id": "manager-pass-2",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "rescue-1",
                    "tool_name": "rescue.run",
                    "arguments": {},
                }
            ],
        },
        {
            "pass_id": "manager-pass-3",
            "action": "final",
            "final_response": {
                "copy": "Baseline manager synthesis without recommendation.",
                "source_tool_call_ids": ["query-1", "rescue-1"],
            },
        },
    ]


def _seed_memory_store(path: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(path)
    write = store.write_memory_events(
        session_id="lab-session-1",
        turn_id="seed-turn",
        events=[
            {
                "memory_id": "reusable-meal-hint-1",
                "memory_type": "pattern_memory",
                "summary": "Mom fried rice maps to reusable meal ufe-fried-rice.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:mt-101"],
                "intended_consumers": ["reusable_meal", "recommendation"],
            },
            {
                "memory_id": "golden-bento-1",
                "memory_type": "golden_order",
                "summary": "Often chooses a FamilyMart chicken bento.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:seed-1"],
                "intended_consumers": ["recommendation", "proactive"],
                "store_name": "FamilyMart",
                "item_names": ["chicken bento"],
                "estimated_kcal": 520,
            },
        ],
    )
    assert write["status"] == "pass"
    return store


def _reusable_meal_entity() -> dict[str, object]:
    return {
        "entity_id": "ufe-fried-rice",
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "display_name": "Mom fried rice",
        "status": "confirmed",
        "review_required": False,
        "current_version_id": "v1",
        "correction_count": 0,
        "drift_status": "stable",
        "version_history": [
            {
                "version_id": "v1",
                "normalized_signature": "mom_fried_rice",
                "source_kind": "mom_bought",
                "estimated_kcal": 650,
                "estimated_kcal_range": {"min": 590, "max": 690},
                "source_refs": ["meal_thread:mt-101"],
            }
        ],
    }
