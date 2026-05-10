from __future__ import annotations

import json

from app.advanced_shadow_lab.dogfood_replay import (
    build_advanced_shadow_dogfood_replay_artifact,
)
from app.memory.application.runtime_lab_dogfood_replay import (
    build_memory_dogfood_replay_review_artifact,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)


def test_dogfood_replay_projects_reviewed_trace_into_advanced_chain() -> None:
    memory_review = build_memory_dogfood_replay_review_artifact([_reviewed_record()])

    artifact = build_advanced_shadow_dogfood_replay_artifact(
        memory_dogfood_replay_review=memory_review,
        chain_payload=_chain_payload(),
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_shadow_dogfood_replay_artifact"
    assert artifact["status"] == "pass"
    assert artifact["source_memory_artifact_type"] == (
        "runtime_lab_memory_dogfood_replay_review"
    )
    assert artifact["reviewed_case_count"] == 1
    assert artifact["dogfood_case_summaries"] == [
        {
            "case_id": "dogfood_rt-lab-dogfood-001",
            "case_type": "explicit_preference",
            "split": "holdout",
            "expected_outcome": "candidate",
            "candidate_type": "preference",
            "source_ref_count": 1,
            "human_review_required": True,
        }
    ]
    assert artifact["advanced_fixture_chain_status"] == "pass"
    assert artifact["terminal_review_sink_summary"] == {
        "status": "pass",
        "record_count": 2,
        "control_path_evidence": {
            "status": "pass",
            "all_candidates_have_required_controls": True,
            "configured_paths": {
                "dismiss": True,
                "snooze": True,
                "undo": True,
            },
            "interaction_actions_observed": ["dismiss", "snooze"],
            "observed_all_interaction_actions": False,
            "next_signal_required_present": True,
        },
    }
    assert [row["status"] for row in artifact["chain_stage_trace"]] == [
        "pass",
        "pass",
        "pass",
        "candidate_for_human_review",
        "candidate_for_human_review",
        "pass",
        "pass",
        "pass",
        "context_available",
        "pass",
        "pass",
    ]
    assert artifact["runtime_connected"] is True
    assert artifact["lab_isolated"] is True
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["delivery_attempted"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private dogfood wording" not in serialized
    assert "hidden-food-candidate" not in serialized
    assert "Fixture headline, not user-facing" not in serialized


def test_dogfood_replay_blocks_missing_scope_before_chain_projection() -> None:
    record = _reviewed_record(request_id="rt-lab-dogfood-missing-scope")
    record["trace"].pop("memory_lab_scope")
    memory_review = build_memory_dogfood_replay_review_artifact([record])

    artifact = build_advanced_shadow_dogfood_replay_artifact(
        memory_dogfood_replay_review=memory_review,
        chain_payload=_chain_payload(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["advanced_fixture_chain_status"] == "not_run"
    assert artifact["terminal_review_sink_summary"] == {
        "status": "not_run",
        "record_count": 0,
        "control_path_evidence": {"status": "not_run"},
    }
    assert artifact["blockers"] == [
        "memory_dogfood_replay_review.status_blocked",
        "memory_dogfood_replay_review.rt-lab-dogfood-missing-scope.missing_scope_keys:workspace_id,project_id,surface,run_id",
    ]
    assert artifact["durable_product_memory_written"] is False


def test_dogfood_replay_blocks_activation_claim_drift() -> None:
    memory_review = build_memory_dogfood_replay_review_artifact([_reviewed_record()])
    memory_review["durable_product_memory_written"] = True
    memory_review["manager_context_packet_changed"] = True

    artifact = build_advanced_shadow_dogfood_replay_artifact(
        memory_dogfood_replay_review=memory_review,
        chain_payload=_chain_payload(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["advanced_fixture_chain_status"] == "not_run"
    assert artifact["blockers"] == [
        "memory_dogfood_replay_review.durable_product_memory_written",
        "memory_dogfood_replay_review.manager_context_packet_changed",
    ]
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["delivery_attempted"] is False


def _reviewed_record(request_id: str = "rt-lab-dogfood-001") -> dict[str, object]:
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
                "run_id": f"{request_id}-run",
            },
            "request": {
                "user_id": "user-a",
                "text": "private dogfood wording should stay redacted",
                "allow_search": False,
            },
            "manager_final_decision": {
                "intent": "log_meal",
                "workflow_effect": "commit_meal_log",
            },
            "memory_lab_candidate_signal": {
                "candidate_type": "preference",
                "manager_decision_field": "memory_candidate_requested",
                "source_refs": [f"message:{request_id}"],
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


def _chain_payload() -> dict[str, object]:
    return {
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": _recommendation_payload(),
        "derived_memory_views": _derived_views(),
        "current_budget_view": _budget_view(),
        "active_body_plan_view": _body_plan_view(),
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "proposal_candidate_output": _proposal_candidate_output(),
        "user_control_models": {
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        "interaction_plan": [
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    }


def _recommendation_payload() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    golden = _candidate(payload, "golden-1")
    golden.update(
        {
            "estimated_kcal": 520,
            "evidence_posture": "exact",
            "availability_posture": "available",
            "realistic_executable": True,
            "user_accessible": True,
            "store_name": "FamilyMart",
            "store_metadata": {"chain": "familymart", "raw_menu_blob": "hidden"},
            "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
            "debug_candidate_copy": "hidden-food-candidate",
        }
    )
    return payload


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for item in payload["candidate_source_fixture"]:  # type: ignore[index]
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise AssertionError(f"candidate not found: {candidate_id}")


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": "golden-1", "store_name": "FamilyMart"}]
        },
        "suppression_summary": {
            "suppression_blockers": [
                {"candidate_id": "suppress-1", "trigger_type": "rescue_nudge"}
            ]
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _derived_views() -> dict[str, object]:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 1,
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def _budget_view() -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "meal_consumption_total_kcal": 2100,
    }


def _body_plan_view() -> dict[str, object]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": 1800,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(5)
        ],
    }


def _proposal_candidate_output() -> dict[str, object]:
    return {
        "proposal_headline": "Fixture headline, not user-facing",
        "proposal_summary": "Fixture summary, not user-facing",
        "coaching_frame": "Fixture frame, not user-facing",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "not_user_facing": True,
            "fixture_only": True,
        },
    }


def _controls(next_signal: str) -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }
