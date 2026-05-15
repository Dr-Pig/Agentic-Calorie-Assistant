from __future__ import annotations

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

COMPLETED_CURRENT_SHELL_STEPS = (
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


def object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def status(value: dict[str, Any]) -> str:
    return str(value.get("status") or "")


def overclaim_blockers(artifact_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{artifact_id}.{flag}"
        for flag in FORBIDDEN_TRUE_CLAIMS
        if payload.get(flag) is True
    ]


def validate_one_day_wall(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    turn_ids = {
        str(turn.get("turn_id"))
        for turn in list(payload.get("turns") or [])
        if isinstance(turn, dict)
    }
    if status(payload) != "pass":
        blockers.append("one_day_wall_not_pass")
    if turn_ids != set(REQUIRED_TURN_IDS):
        blockers.append("one_day_wall_turn_sequence_missing")
    summary = object_dict(payload.get("summary"))
    if summary.get("final_consumed_kcal") != 1670:
        blockers.append("one_day_wall_final_consumed_kcal_mismatch")
    if summary.get("final_remaining_kcal") != 130:
        blockers.append("one_day_wall_final_remaining_kcal_mismatch")
    return blockers


def validate_reopen_continuity(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if status(payload) != "pass":
        blockers.append("reopen_continuity_not_pass")
    if payload.get("read_only") is not True or payload.get("mutation_applied") is not False:
        blockers.append("reopen_continuity_not_read_only")
    summary = object_dict(payload.get("summary"))
    if summary.get("final_consumed_kcal") != 1670:
        blockers.append("reopen_final_consumed_kcal_mismatch")
    if summary.get("final_remaining_kcal") != 130:
        blockers.append("reopen_final_remaining_kcal_mismatch")
    if summary.get("same_truth_status") != "pass":
        blockers.append("reopen_same_truth_not_pass")
    return blockers


def validate_browser_realistic(payload: dict[str, Any]) -> tuple[list[str], bool]:
    if status(payload) == "blocked" or payload.get("browser_executed") is False:
        return ["browser_realistic_not_executed"], False
    blockers: list[str] = []
    if status(payload) not in BROWSER_DIAGNOSTIC_PASS_STATUSES:
        blockers.append("browser_realistic_not_diagnostic_pass")
    if payload.get("browser_executed") is not True:
        blockers.append("browser_realistic_not_executed")
    if payload.get("fixture_evidence_used") is not True:
        blockers.append("browser_realistic_fixture_evidence_missing")
    browser = object_dict(payload.get("browser"))
    for field, blocker in (
        ("target_update_rendered", "target_update_not_rendered"),
        ("chat_history_reloaded", "chat_history_not_reloaded"),
        ("today_summary_rendered", "today_summary_not_rendered"),
        ("debug_surface_rendered", "debug_surface_not_rendered"),
    ):
        if browser.get(field) is not True:
            blockers.append(blocker)
    return blockers, True


def validate_context_replay(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if status(payload) != "generated":
        blockers.append("context_replay_not_generated")
    if int(payload.get("scenario_count") or 0) < 12:
        blockers.append("context_replay_scenario_count_too_low")
    summary = object_dict(payload.get("summary"))
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


def validate_fake_provider_smoke(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if status(payload) != "pass":
        blockers.append("fake_provider_smoke_not_pass")
    if payload.get("final_semantic_decision_source") != "fixture_manager_structured_decision":
        blockers.append("fake_provider_semantic_source_not_fixture_manager")
    if payload.get("deterministic_semantic_inference_used") is not False:
        blockers.append("fake_provider_deterministic_semantic_inference")
    if payload.get("raw_text_intent_router_used") is not False:
        blockers.append("fake_provider_raw_text_router_used")
    return blockers
