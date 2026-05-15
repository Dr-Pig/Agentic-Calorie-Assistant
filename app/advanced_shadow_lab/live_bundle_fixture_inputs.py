from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_dogfood_replay import build_memory_dogfood_replay_review_artifact
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.live_bundle_fixture_inputs")
FALSE_FLAGS = dict.fromkeys(
    (
        "live_provider_invoked", "live_provider_used", "mainline_runtime_connected",
        "mainline_route_or_api_mount_allowed", "production_scheduler_delivery_allowed",
        "production_db_migration_allowed", "canonical_product_mutation_allowed",
        "manager_context_packet_changed", "manager_context_injected",
        "recommendation_served", "rescue_committed", "proposal_committed",
        "durable_product_memory_written", "durable_memory_written",
        "mutation_changed", "user_facing_behavior_changed", "product_readiness_claimed",
    ),
    False,
)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_canonical_mutation_authority",
]


def build_live_bundle_memory_review() -> dict[str, Any]:
    return build_memory_dogfood_replay_review_artifact([_reviewed_memory_record()])


def build_live_bundle_chain_payload() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_shadow_live_bundle_chain_payload",
        "artifact_schema_version": "1.0",
        "owner": "app/advanced_shadow_lab/live_bundle_fixture_inputs.py",
        "consumer": "scripts/run_advanced_shadow_lab_live_bundle.py",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": _recommendation_payload(),
        "derived_memory_views": _derived_views(),
        "current_budget_view": _budget_view(),
        "active_body_plan_view": _body_plan_view(),
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "proposal_candidate_output": _proposal_candidate_output(),
        "user_control_models": {
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "pending_intake_followup": _controls("user_confirms_or_cancels_pending_intake"),
            "rescue_nudge": _controls("material_budget_change_or_user_reopens_rescue"),
        },
        "interaction_plan": [
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _reviewed_memory_record() -> dict[str, Any]:
    request_id = "rt-lab-synthetic-live-bundle-001"
    return {
        "trace": {
            "request_id": request_id,
            "trace_meta": {
                "request_id": request_id,
                "user_id": "synthetic-user",
                "bundle": "advanced_shadow_lab",
                "local_date": "2026-05-10",
            },
            "memory_lab_scope": {
                "workspace_id": "synthetic-workspace",
                "project_id": "advanced-memory-runtime-lab",
                "surface": "advanced_shadow_lab_live_bundle",
                "run_id": f"{request_id}-run",
            },
            "request": {"user_id": "synthetic-user", "text": "redacted synthetic preference"},
            "manager_final_decision": {"intent": "log_meal", "workflow_effect": "commit_meal_log"},
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
            "reviewer_id": "synthetic-human-reviewer",
            "case_type": "explicit_preference",
            "split": "holdout",
            "expected_outcome": "candidate",
            "expected_candidate_type": "preference",
            "semantic_oracle_source": "product_rule_and_trace_fields",
            "raw_keyword_route_allowed": False,
            "source_ref_confirmation": True,
        },
    }


def _memory_projection() -> dict[str, Any]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {"orders": [{"candidate_id": "golden-1"}]},
        "suppression_summary": {"suppression_blockers": []},
        **dict(FALSE_FLAGS),
    }


def _recommendation_payload() -> dict[str, Any]:
    payload = build_fixture_recommendation_three_node_input()
    _candidate(payload, "golden-1").update(
        {
            "title": "Chicken salad",
            "store_name": "FamilyMart",
            "estimated_kcal": 520,
            "evidence_posture": "exact",
            "availability_posture": "available",
            "realistic_executable": True,
            "user_accessible": True,
            "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
        }
    )
    return payload


def _candidate(payload: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    for item in payload.get("candidate_source_fixture") or []:
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise ValueError(f"candidate_not_found:{candidate_id}")


def _budget_view() -> dict[str, int | str]:
    return {
        "local_date": "2026-05-10",
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "remaining_budget_kcal": -300,
        "overshoot_kcal": 300,
        "meal_consumption_total_kcal": 2100,
    }


def _derived_views() -> dict[str, Any]:
    return {
        "rescue_history_summary": {"is_durable_memory_truth": False, "rescue_event_count": 1},
        "adherence_summary": {"is_durable_memory_truth": False, "adherence_posture": "mixed"},
    }


def _body_plan_view() -> dict[str, Any]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {"local_date": "2026-05-10", "base_budget_kcal": 1800},
            {"local_date": "2026-05-11", "base_budget_kcal": 1800},
        ],
    }


def _proposal_candidate_output() -> dict[str, Any]:
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


def _controls(next_signal: str) -> dict[str, Any]:
    return {
        "dismiss_reason_choices": ["not_relevant_now", "already_handled", "too_frequent"],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }
__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_live_bundle_chain_payload", "build_live_bundle_memory_review"]
