from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.paired_fixture_cases"
)
ARTIFACT_TYPE = "advanced_shadow_paired_fixture_cases"
FIXTURE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
CASE_FALSE_FLAGS = (
    "runtime_connected",
    "delivery_attempted",
    "recommendation_served",
    "rescue_committed",
    "proposal_committed",
    "mutation_changed",
    "user_facing_behavior_changed",
    "product_readiness_claimed",
)
CASE_DEFINITIONS = [
    (
        "F",
        "same_day_rescue_after_overshoot",
        "rescue_same_day",
        (
            "rescue_shadow_chain_runner_artifact",
            "rescue_chat_negotiation_lifecycle_shadow_packet",
            "advanced_shadow_chat_ux_packet_artifact",
        ),
    ),
    (
        "F2",
        "planned_event_rescue_before_large_meal",
        "rescue_planned_event",
        (
            "rescue_proposal_shaping_input_shadow_packet",
            "rescue_planned_event_negotiation_shadow_packet",
        ),
    ),
    (
        "I",
        "calibration_proposal_from_body_trend",
        "calibration_proposal",
        (
            "body_calibration_diagnostic_result",
            "calibration_proposal_policy_packet",
            "calibration_proposal_response_result",
        ),
    ),
    (
        "L",
        "contextual_recommendation_to_pending_meal_intent",
        "recommendation_pending_meal_intent",
        (
            "recommendation_three_node_shadow_artifact",
            "recommendation_offer_shadow_packet",
            "recommendation_pending_meal_intent_shadow_packet",
        ),
    ),
    (
        "M",
        "preference_memory_affects_recommendation",
        "memory_affects_recommendation",
        (
            "runtime_lab_memory_consumer_summary_projection",
            "memory_lab_review_loop_state",
            "chat_first_memory_review_correction_surface",
            "recommendation_three_node_shadow_artifact",
        ),
    ),
    (
        "N",
        "proactive_chat_first_no_send_intervention",
        "proactive_no_send",
        (
            "proactive_no_send_nudge_candidate_bridge",
            "proactive_pending_meal_followup_shadow",
            "proactive_no_send_review_sink_artifact",
            "advanced_shadow_chat_ux_packet_artifact",
        ),
    ),
]


def build_paired_fixture_case_artifacts(
    *, fixture_chain_artifact: Mapping[str, Any]
) -> dict[str, Any]:
    blockers = _source_blockers(fixture_chain_artifact)
    if blockers:
        baseline: list[dict[str, Any]] = []
        advanced: list[dict[str, Any]] = []
    else:
        baseline = [_case(case, "baseline_fixture_trace") for case in CASE_DEFINITIONS]
        advanced = [_case(case, "advanced_shadow_fixture_trace") for case in CASE_DEFINITIONS]
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/paired_fixture_cases.py",
        "consumer": "advanced_shadow_comparison_artifact.paired_case_rows",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "new_report_family_created": False,
        "semantic_truth_owner": "source_artifacts_not_pairing_generator",
        "claim_boundary": "non_claim",
        "case_ids": [case_id for case_id, _, _, _ in CASE_DEFINITIONS],
        "baseline_case_artifacts": baseline,
        "advanced_case_artifacts": advanced,
        "blockers": blockers,
        "runtime_connected": False,
        "product_readiness_claimed": False,
    }


def _source_blockers(source: Mapping[str, Any]) -> list[str]:
    return [
        *_source_type_status_blockers(source),
        *_terminal_artifact_blockers(source),
        *_activation_flag_blockers(source),
    ]


def _source_type_status_blockers(source: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if source.get("artifact_type") != FIXTURE_TYPE:
        blockers.append(f"fixture_chain.unsupported_artifact_type:{source.get('artifact_type') or 'missing'}")
    if source.get("status") != "pass":
        blockers.append(f"fixture_chain.status_{source.get('status') or 'missing'}")
    return blockers


def _terminal_artifact_blockers(source: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    sink = _mapping(source.get("terminal_review_sink"))
    if sink.get("status") != "pass":
        blockers.append(f"terminal_review_sink.status_{sink.get('status') or 'missing'}")
    chat = _mapping(source.get("chat_ux_packet"))
    if chat.get("status") != "pass":
        blockers.append(f"chat_ux_packet.status_{chat.get('status') or 'missing'}")
    return blockers


def _activation_flag_blockers(source: Mapping[str, Any]) -> list[str]:
    return [
        f"fixture_chain.{flag}"
        for flag in FALSE_FLAG_NAMES
        if source.get(flag) is True
    ]


def _case(
    case: tuple[str, str, str, tuple[str, ...]],
    artifact_type: str,
) -> dict[str, Any]:
    journey_id, journey_name, surface, source_refs = case
    return {
        "case_id": journey_id,
        "journey_id": journey_id,
        "journey_name": journey_name,
        "artifact_type": artifact_type,
        "status": "pass",
        "technical_surface": surface,
        "source_artifact_refs": list(source_refs),
        "observable_output_summary": {
            "status": "pass",
            "comparison_scope": "ux_journey_fixture_shape_only",
        },
        "semantic_truth_owner": "source_artifacts_not_pairing_generator",
        "semantic_decision_inferred_by_runner": False,
        **dict.fromkeys(CASE_FALSE_FLAGS, False),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_paired_fixture_case_artifacts",
]
