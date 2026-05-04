from __future__ import annotations

import json
from pathlib import Path

from app.rescue.application.shadow_candidate_artifact import (
    build_rescue_shadow_candidates_artifact,
)
from app.rescue.application.shadow_option_generator import generate_rescue_option_packet
from app.rescue.application.shadow_trigger_detector import detect_rescue_trigger_candidate
from app.rescue.application.shadow_viability_scorer import score_rescue_viability
from app.rescue.fixtures.shadow_scenarios import (
    rescue_shadow_scenario_fixture_pairs,
    rescue_shadow_scenario_ids,
)


EXPECTED_SCENARIO_IDS = {
    "small_overshoot_no_rescue_needed",
    "large_overshoot_candidate_rescue",
    "low_logging_quality_downgrades_confidence",
    "repeated_overshoot_pattern",
    "calibration_uncertain_no_overcorrect",
    "user_dislikes_strict_plans",
    "existing_open_proposal_blocks_duplicate",
    "no_active_budget_or_body_plan_blocks",
}


def _scenario_outputs(scenario_id: str):
    context = dict(rescue_shadow_scenario_fixture_pairs())[scenario_id]
    trigger = detect_rescue_trigger_candidate(context)
    viability = score_rescue_viability(context, trigger)
    option_packet = generate_rescue_option_packet(context, trigger, viability)
    return trigger, viability, option_packet


def test_rs6_declares_all_minimum_scenario_fixtures() -> None:
    assert set(rescue_shadow_scenario_ids()) == EXPECTED_SCENARIO_IDS


def test_small_overshoot_fixture_is_informational_only() -> None:
    trigger, viability, option_packet = _scenario_outputs(
        "small_overshoot_no_rescue_needed"
    )

    assert trigger.should_generate_rescue_candidate is False
    assert viability.viability_band == "not_needed"
    assert viability.recommended_action == "discard"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "informational_only"
    }
    assert option_packet.selected_shadow_option_id == option_packet.option_candidates[0].option_id


def test_large_overshoot_fixture_generates_soft_spread_candidate() -> None:
    trigger, viability, option_packet = _scenario_outputs(
        "large_overshoot_candidate_rescue"
    )

    assert trigger.should_generate_rescue_candidate is True
    assert viability.viability_band == "medium"
    assert viability.recommended_action == "promote_later"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "multi_day_spread_candidate"
    }


def test_low_logging_quality_fixture_downgrades_confidence_and_asks_user() -> None:
    _trigger, viability, option_packet = _scenario_outputs(
        "low_logging_quality_downgrades_confidence"
    )

    assert "low_logging_quality" in viability.reason_codes
    assert viability.confidence < 0.6
    assert viability.recommended_action == "ask_user"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "ask_user_context_first"
    }


def test_repeated_overshoot_fixture_flags_pattern_and_promote_later() -> None:
    trigger, viability, option_packet = _scenario_outputs("repeated_overshoot_pattern")

    assert trigger.trigger_candidate == "repeated_overshoot_pattern"
    assert "repeated_overshoot" in viability.reason_codes
    assert viability.recommended_action == "promote_later"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "ask_user_context_first"
    }
    assert "repeated_overshoot_strategy_review" in option_packet.reason_codes
    assert option_packet.selected_shadow_option_id == option_packet.option_candidates[0].option_id
    assert option_packet.runtime_effect_allowed is False


def test_calibration_uncertain_fixture_avoids_overcorrection() -> None:
    _trigger, viability, option_packet = _scenario_outputs(
        "calibration_uncertain_no_overcorrect"
    )

    assert "recent_calibration_uncertain" in viability.reason_codes
    assert viability.recommended_action == "ask_user"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "ask_user_context_first"
    }
    assert "multi_day_spread_candidate" not in {
        option.option_type for option in option_packet.option_candidates
    }


def test_user_dislikes_strict_plans_fixture_softens_option() -> None:
    _trigger, viability, option_packet = _scenario_outputs("user_dislikes_strict_plans")

    assert "user_likely_dislikes_strict_plans" in viability.reason_codes
    assert viability.recommended_action == "ask_user"
    assert {option.option_type for option in option_packet.option_candidates} == {
        "ask_user_context_first"
    }


def test_existing_open_proposal_fixture_blocks_duplicate_candidate() -> None:
    trigger, viability, option_packet = _scenario_outputs(
        "existing_open_proposal_blocks_duplicate"
    )

    assert trigger.should_generate_rescue_candidate is False
    assert trigger.why_no_rescue_candidate == "open_proposal_exists"
    assert "existing_open_proposal" in viability.reason_codes
    assert option_packet.option_candidates == ()
    assert option_packet.options_rejected[0].reason_code == "existing_open_proposal"


def test_no_active_budget_or_body_plan_fixture_blocks_candidate() -> None:
    trigger, viability, option_packet = _scenario_outputs(
        "no_active_budget_or_body_plan_blocks"
    )

    assert trigger.should_generate_rescue_candidate is False
    assert trigger.why_no_rescue_candidate == "no_active_budget_or_body_plan"
    assert "no_active_plan" in viability.reason_codes
    assert option_packet.option_candidates == ()
    assert option_packet.options_rejected[0].reason_code == "no_active_plan"


def test_rs6_scenarios_build_shadow_candidates_artifact_without_runtime_effects() -> None:
    artifact = build_rescue_shadow_candidates_artifact(
        scenarios=rescue_shadow_scenario_fixture_pairs()
    )
    payload = artifact.model_dump(mode="json")

    assert payload["summary"]["candidate_count"] == len(EXPECTED_SCENARIO_IDS)
    assert payload["shadow_mode"] is True
    assert payload["real_runtime_effect"] is False
    assert payload["rescue_committed"] is False
    assert all(
        candidate["runtime_effect_allowed"] is False
        for candidate in payload["rescue_shadow_candidates"]
    )
    json.dumps(payload, ensure_ascii=False)


def test_rs6_scenario_fixture_pairs_return_deep_copies() -> None:
    first_pairs = dict(rescue_shadow_scenario_fixture_pairs())
    second_pairs = dict(rescue_shadow_scenario_fixture_pairs())

    first_context = first_pairs["small_overshoot_no_rescue_needed"]
    second_context = second_pairs["small_overshoot_no_rescue_needed"]

    assert first_context is not second_context
    assert first_context.current_budget is not second_context.current_budget
    first_context.current_budget.remaining_kcal = -999
    assert second_context.current_budget.remaining_kcal == -80


def test_rs6_scenarios_script_output_can_include_full_fixture_set(tmp_path: Path) -> None:
    from scripts.build_rescue_shadow_candidates import main

    output_path = tmp_path / "rescue_shadow_candidates.json"
    exit_code = main(["--scenario-set", "rs6_minimum", "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["candidate_count"] == len(EXPECTED_SCENARIO_IDS)
    assert set(payload["summary"]["scenario_ids"]) == EXPECTED_SCENARIO_IDS
