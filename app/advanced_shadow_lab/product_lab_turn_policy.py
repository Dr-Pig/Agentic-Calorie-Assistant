from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


LAB_MODE = "isolated_advanced_product_lab"
SUPPORTED_FIXTURE_INTENTS = {
    "advanced_recommendation_rescue_proactive_loop",
    "calibration_proposal_from_body_trend",
    "no_plan_degraded_journey",
    "pre_meal_planning",
    "swap_suggestion",
}
CAPABILITIES_EXERCISED = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "proactive",
    "chat_first_controls",
]
MERGE_BACK_ACTIVATION_WALL = {
    "mainline_activation_requires_separate_pr": True,
    "self_use_v1_route_or_startup_changed": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "manager_context_packet_changed": False,
}
NON_CLAIMS = [
    "not_self_use_v1_runtime",
    "not_mainline_runtime_activation",
    "not_production_scheduler",
    "not_production_db_migration",
    "not_canonical_mutation",
    "not_durable_product_memory_activation",
]


def turn_blockers(*, lab_mode: str, turn: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if lab_mode != LAB_MODE:
        blockers.append("lab_mode.not_isolated_advanced_product_lab")
    intent = str(turn.get("semantic_intent_fixture") or "")
    if not intent:
        blockers.append("turn.semantic_intent_fixture_missing")
    elif intent not in SUPPORTED_FIXTURE_INTENTS:
        blockers.append(f"turn.semantic_intent_fixture_unsupported:{intent}")
    if str(turn.get("surface") or "") != "chat":
        blockers.append("turn.surface_not_chat")
    if not str(turn.get("session_id") or ""):
        blockers.append("turn.session_id_missing")
    if not str(turn.get("turn_id") or ""):
        blockers.append("turn.turn_id_missing")
    return blockers


def blocked_turn(
    *,
    turn: Mapping[str, Any],
    lab_mode: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        **base_turn(turn=turn, lab_mode=lab_mode),
        "status": "blocked",
        "full_product_lab_runtime_enabled": False,
        "lab_user_facing_behavior_changed": False,
        "product_capabilities_exercised": [],
        "e2e_chain_artifact": None,
        "control_state": None,
        "lab_chat_response_packet": None,
        "lab_chat_surface": None,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def base_turn(*, turn: Mapping[str, Any], lab_mode: str) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_turn_artifact",
        "artifact_schema_version": "1.0",
        "owner": "app/advanced_shadow_lab/product_lab_runtime.py",
        "consumer": "advanced_product_lab_fixture_live_and_e2e_tests",
        "retirement_trigger": "approved_advanced_product_lab_merge_back_plan",
        "lab_mode": lab_mode,
        "session_id": str(turn.get("session_id") or ""),
        "turn_id": str(turn.get("turn_id") or ""),
        "surface": str(turn.get("surface") or ""),
        "chat_first_surface": str(turn.get("surface") or "") == "chat",
        "semantic_intent_fixture": str(turn.get("semantic_intent_fixture") or ""),
        "raw_user_text_semantic_inference_performed": False,
        "merge_back_activation_wall": dict(MERGE_BACK_ACTIVATION_WALL),
        "non_claims": list(NON_CLAIMS),
    }


def mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    return value if isinstance(value, Mapping) else {}


def control_models(source: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    value = source.get("user_control_models")
    return value if isinstance(value, Mapping) else {}


def interaction_plan(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = source.get("interaction_plan")
    return [item for item in value or [] if isinstance(item, Mapping)]


def lab_now_minute(turn: Mapping[str, Any]) -> int:
    value = turn.get("lab_now_minute")
    return value if isinstance(value, int) else 0


def observed_material_signals(turn: Mapping[str, Any]) -> list[str]:
    return [str(item) for item in turn.get("observed_material_signals") or []]


def stage_blockers(stage_name: str, artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("status") == "pass":
        return []
    return [f"{stage_name}.{blocker}" for blocker in artifact.get("blockers") or []]
