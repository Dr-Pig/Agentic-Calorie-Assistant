from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.chat_first_journey_proof import build_chat_first_journey_proof
from app.advanced_shadow_lab.e2e_fixture_chain import run_advanced_shadow_e2e_fixture_chain
from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import build_consumer_summary_projection_from_shadow_memory_context_pack
from app.memory.application.runtime_lab_reviewed_memory_retrieval import build_shadow_memory_context_pack_from_reviewed_store
from app.memory.application.runtime_lab_reviewed_memory_store import RuntimeLabReviewedMemoryStore
from app.recommendation.application.three_node_shadow_contract import build_fixture_recommendation_three_node_input
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.vertical_proof_lineage")
REAL_STAGE_ORDER = [
    "runtime_lab_reviewed_memory_store_write",
    "shadow_memory_context_pack",
    "runtime_lab_memory_consumer_summary_projection",
    "advanced_shadow_e2e_fixture_chain_artifact",
    "proactive_no_send_review_sink_artifact",
    "advanced_shadow_chat_ux_packet_artifact",
    "advanced_shadow_chat_first_journey_proof_artifact",
]


REVIEWED_MEMORY_ROWS = (
    ("golden-order-morning-bar-oatmeal-latte", "golden_order", "User often chooses FamilyMart salad chicken and sweet potato."),
    ("negative-preference-ingredient-cilantro", "negative_preference", "User explicitly avoids cilantro."),
)


def build_real_artifact_lineage(*, scope: Mapping[str, Any], artifact_root: Path | str) -> dict[str, Any]:
    store = RuntimeLabReviewedMemoryStore(artifact_root)
    memory_write = store.write_review_loop_state({"lab_memory_records": _reviewed_memory_records(scope)})
    context_pack = build_shadow_memory_context_pack_from_reviewed_store(store, scope, token_budget=160)
    memory_projection = build_consumer_summary_projection_from_shadow_memory_context_pack(context_pack)
    fixture_chain = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=memory_projection,
        recommendation_payload=_recommendation_payload(memory_projection),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_proposal_candidate_output(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls("material_budget_change_or_user_reopens_rescue"),
        },
        interaction_plan=[
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    )
    journey_proof = build_chat_first_journey_proof(
        context_pack=context_pack,
        memory_projection=memory_projection,
        fixture_chain=fixture_chain,
        terminal_sink=fixture_chain["terminal_review_sink"],
        chat_packet=fixture_chain["chat_ux_packet"],
    )
    stages = [
        memory_write,
        context_pack,
        memory_projection,
        fixture_chain,
        fixture_chain["terminal_review_sink"],
        fixture_chain["chat_ux_packet"],
        journey_proof,
    ]
    return {
        "stage_artifacts": stages,
        "artifact_lineage": [_lineage_row(stage) for stage in stages],
        "blockers": _stage_status_blockers(stages),
        "lab_delivery_record": {
            "sink": "isolated_lab_sink",
            "delivery_mode": "record_only",
            "source_artifact_type": "proactive_no_send_review_sink_artifact",
            "record_count": int(fixture_chain["terminal_review_sink"]["record_count"]),
            "delivered_to_production": False,
        },
    }


def _reviewed_memory_records(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _memory_record(scope, candidate_id, candidate_type, memory_text)
        for candidate_id, candidate_type, memory_text in REVIEWED_MEMORY_ROWS
    ]


def _memory_record(
    scope: Mapping[str, Any],
    candidate_id: str,
    candidate_type: str,
    memory_text: str,
) -> dict[str, Any]:
    return {
        "memory_record_id": f"lab-shadow-memory-record-{candidate_id}",
        "source_candidate_id": candidate_id,
        "source_action_id": f"review-{candidate_id}",
        "record_state": "accepted_shadow",
        "revision": 1,
        "memory_text": memory_text,
        "candidate_type": candidate_type,
        "scope_keys": dict(scope),
        "intended_consumers": ["recommendation_shadow", "proactive_shadow"],
        "active_in_lab_context": True,
        "audit_provenance_retained": True,
        "provenance": {"source_object_refs": [f"memory_candidate:{candidate_id}"]},
        "audit_log": [{"action": "accepted_shadow", "actor": "fixture_reviewer"}],
    }


def _recommendation_payload(memory_projection: Mapping[str, Any]) -> dict[str, Any]:
    payload = build_fixture_recommendation_three_node_input()
    payload["memory_summary_projection"] = memory_projection
    for candidate in payload["candidate_source_fixture"]:
        if candidate["candidate_id"] == "golden-1":
            candidate.update(
                {
                    "estimated_kcal": 520,
                    "evidence_posture": "exact",
                    "availability_posture": "available",
                    "realistic_executable": True,
                    "user_accessible": True,
                    "store_name": "FamilyMart",
                    "store_metadata": {"chain": "familymart"},
                    "source_refs": [
                        "memory_candidate:golden-order-morning-bar-oatmeal-latte"
                    ],
                }
            )
    return payload


def _derived_views() -> dict[str, Any]:
    return {
        "rescue_history_summary": {"is_durable_memory_truth": False, "rescue_event_count": 1},
        "adherence_summary": {"is_durable_memory_truth": False, "adherence_posture": "mixed"},
    }


def _budget_view() -> dict[str, int]:
    return {"base_budget_kcal": 1800, "effective_budget_kcal": 1800, "meal_consumption_total_kcal": 2100}


def _body_plan_view() -> dict[str, Any]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {"local_date": f"2026-05-{10 + index:02d}", "base_budget_kcal": 1800, "calibration_adjustment_total_kcal": 0}
            for index in range(5)
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
        "rubric": {"future_oriented": True, "no_shame": True, "not_user_facing": True, "fixture_only": True},
    }


def _controls(next_signal: str) -> dict[str, Any]:
    return {
        "dismiss_reason_choices": ["not_relevant_now", "already_handled", "too_frequent"],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }


def _lineage_row(stage: Mapping[str, Any]) -> dict[str, str]:
    return {
        "artifact_type": str(stage.get("artifact_type") or ""),
        "status": str(stage.get("status") or ""),
    }


def _stage_status_blockers(stages: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{stage.get('artifact_type')}.status_{stage.get('status')}"
        for stage in stages
        if stage.get("status") != "pass"
    ]


__all__ = ["REAL_STAGE_ORDER", "SIDECAR_ACTIVATION_CONTRACT", "build_real_artifact_lineage"]
