from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

REQUIRED_TURN_IDS = (
    "breakfast_tea_egg_latte",
    "lunch_chicken_bento",
    "lunch_rice_less_correction",
    "bubble_tea_first_value",
    "bubble_tea_half_sugar_large_refinement",
    "dinner_luwei_bare_draft",
    "dinner_luwei_listed_commit",
    "dinner_remove_gongwan",
    "today_consumed_remaining_query",
)

COMPLETED_PRODUCT_LOOP_STEPS = (
    "target_update",
    "food_log",
    "listed_basket_commit",
    "correction",
    "removal",
    "remaining_query",
    "reload_continuity",
    "browser_render_same_truth",
    "context_replay",
    "fake_provider_context_smoke",
)

FORBIDDEN_TRUE_CLAIMS = (
    "fooddb_evidence_used",
    "websearch_evidence_used",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "live_llm_invoked",
    "web_tavily_used",
    "web_tavily_invoked",
    "fooddb_truth_updated",
)

BROWSER_DIAGNOSTIC_PASS_STATUSES = {
    "browser_diagnostic_pass_with_fixture_evidence_gap",
    "browser_diagnostic_pass_with_evidence_gap",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(value: dict[str, Any]) -> str:
    return str(value.get("status") or "")


def _turn_ids(one_day_wall: dict[str, Any]) -> set[str]:
    return {
        str(turn.get("turn_id"))
        for turn in list(one_day_wall.get("turns") or [])
        if isinstance(turn, dict)
    }


def _overclaim_blockers(artifact_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{artifact_id}.{flag}"
        for flag in FORBIDDEN_TRUE_CLAIMS
        if payload.get(flag) is True
    ]


def _validate_one_day_wall(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != "pass":
        blockers.append("one_day_wall_not_pass")
    if _turn_ids(payload) != set(REQUIRED_TURN_IDS):
        blockers.append("one_day_wall_turn_sequence_missing")
    summary = _object_dict(payload.get("summary"))
    if summary.get("final_consumed_kcal") != 1670:
        blockers.append("one_day_wall_final_consumed_kcal_mismatch")
    if summary.get("final_remaining_kcal") != 130:
        blockers.append("one_day_wall_final_remaining_kcal_mismatch")
    return blockers


def _validate_reopen_continuity(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != "pass":
        blockers.append("reopen_continuity_not_pass")
    if payload.get("read_only") is not True or payload.get("mutation_applied") is not False:
        blockers.append("reopen_continuity_not_read_only")
    summary = _object_dict(payload.get("summary"))
    if summary.get("final_consumed_kcal") != 1670:
        blockers.append("reopen_final_consumed_kcal_mismatch")
    if summary.get("final_remaining_kcal") != 130:
        blockers.append("reopen_final_remaining_kcal_mismatch")
    if summary.get("same_truth_status") != "pass":
        blockers.append("reopen_same_truth_not_pass")
    return blockers


def _validate_browser_realistic(payload: dict[str, Any]) -> tuple[list[str], bool]:
    if _status(payload) == "blocked" or payload.get("browser_executed") is False:
        return ["browser_realistic_not_executed"], False
    blockers: list[str] = []
    if _status(payload) not in BROWSER_DIAGNOSTIC_PASS_STATUSES:
        blockers.append("browser_realistic_not_diagnostic_pass")
    if payload.get("browser_executed") is not True:
        blockers.append("browser_realistic_not_executed")
    if payload.get("fixture_evidence_used") is not True:
        blockers.append("browser_realistic_fixture_evidence_missing")
    browser = _object_dict(payload.get("browser"))
    for field, blocker in (
        ("target_update_rendered", "target_update_not_rendered"),
        ("chat_history_reloaded", "chat_history_not_reloaded"),
        ("today_summary_rendered", "today_summary_not_rendered"),
        ("debug_surface_rendered", "debug_surface_not_rendered"),
    ):
        if browser.get(field) is not True:
            blockers.append(blocker)
    return blockers, True


def _validate_context_replay(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != "generated":
        blockers.append("context_replay_not_generated")
    if int(payload.get("scenario_count") or 0) < 12:
        blockers.append("context_replay_scenario_count_too_low")
    summary = _object_dict(payload.get("summary"))
    if int(summary.get("pending_pin_scenarios") or 0) < 3:
        blockers.append("context_replay_pending_pin_scenarios_too_low")
    if int(summary.get("manager_semantic_required_scenarios") or 0) < 1:
        blockers.append("context_replay_manager_semantic_required_missing")
    if int(summary.get("outside_current_day_omitted_scenarios") or 0) < 1:
        blockers.append("context_replay_outside_current_day_omitted_missing")
    if payload.get("deterministic_supplies_candidates_and_pins_only") is not True:
        blockers.append("context_replay_candidate_pin_boundary_missing")
    if payload.get("deterministic_semantic_inference_used") is not False:
        blockers.append("context_replay_deterministic_semantic_inference")
    if payload.get("raw_text_intent_router_used") is not False:
        blockers.append("context_replay_raw_text_router_used")
    if payload.get("mutation_authority") is not False:
        blockers.append("context_replay_mutation_authority")
    return blockers


def _validate_fake_provider_smoke(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) != "pass":
        blockers.append("fake_provider_smoke_not_pass")
    if payload.get("final_semantic_decision_source") != "fixture_manager_structured_decision":
        blockers.append("fake_provider_semantic_source_not_fixture_manager")
    if payload.get("deterministic_semantic_inference_used") is not False:
        blockers.append("fake_provider_deterministic_semantic_inference")
    if payload.get("raw_text_intent_router_used") is not False:
        blockers.append("fake_provider_raw_text_router_used")
    return blockers


def build_fixture_full_product_loop_e2e_artifact(
    *,
    one_day_wall: dict[str, Any],
    reopen_continuity: dict[str, Any],
    browser_realistic: dict[str, Any],
    context_replay: dict[str, Any],
    fake_provider_context_smoke: dict[str, Any],
) -> dict[str, Any]:
    inputs = {
        "one_day_wall": _object_dict(one_day_wall),
        "reopen_continuity": _object_dict(reopen_continuity),
        "browser_realistic": _object_dict(browser_realistic),
        "context_replay": _object_dict(context_replay),
        "fake_provider_context_smoke": _object_dict(fake_provider_context_smoke),
    }
    blockers: list[str] = []
    for artifact_id, payload in inputs.items():
        blockers.extend(_overclaim_blockers(artifact_id, payload))
    blockers.extend(_validate_one_day_wall(inputs["one_day_wall"]))
    blockers.extend(_validate_reopen_continuity(inputs["reopen_continuity"]))
    browser_blockers, browser_executed = _validate_browser_realistic(inputs["browser_realistic"])
    blockers.extend(browser_blockers)
    blockers.extend(_validate_context_replay(inputs["context_replay"]))
    blockers.extend(_validate_fake_provider_smoke(inputs["fake_provider_context_smoke"]))

    if any("." in blocker for blocker in blockers):
        status = "fail"
    elif blockers == ["browser_realistic_not_executed"]:
        status = "blocked_browser_execution_unavailable"
    elif blockers:
        status = "fail"
    else:
        status = "fixture_product_loop_e2e_diagnostic_pass"

    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
            "claim_scope": "fixture_full_product_loop_e2e_diagnostic",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "blockers": blockers,
            "completed_product_loop_steps": list(COMPLETED_PRODUCT_LOOP_STEPS)
            if status == "fixture_product_loop_e2e_diagnostic_pass"
            else [
                step
                for step in COMPLETED_PRODUCT_LOOP_STEPS
                if step not in {"browser_render_same_truth"}
            ],
            "browser_executed": browser_executed,
            "local_only": True,
            "diagnostic_only": True,
            "ready_for_fdb_integration": False,
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "manager_context_packet_schema_changed": False,
            "frontend_semantic_owner": False,
            "semantic_owner_summary": {
                "user_intent": "fixture_manager_structured_decision",
                "food_semantics": "fixture_evidence_only",
                "mutation_legality": "runtime_guard",
                "persistence_truth": "local_sqlite_canonical_state",
                "frontend": "render_only",
            },
            "input_statuses": {
                artifact_id: {
                    "status": _status(payload),
                    "artifact_type": payload.get("artifact_type")
                    or payload.get("scenario_wall_id")
                    or payload.get("continuity_id")
                    or "unknown",
                }
                for artifact_id, payload in inputs.items()
            },
        }
    )


__all__ = [
    "build_fixture_full_product_loop_e2e_artifact",
]
