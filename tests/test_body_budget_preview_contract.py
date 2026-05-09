from __future__ import annotations

from app.body.application.body_budget_preview_contract import (
    build_body_budget_preview_contract_artifact,
)


REQUIRED_CASES = [
    "weight_observation_chat_preview",
    "body_fat_answer_only_boundary",
    "exercise_met_estimate_preview",
    "exercise_user_asserted_preview",
    "effective_budget_what_if_projection",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_body_budget_preview_contract_is_no_runtime_fixture_only() -> None:
    artifact = build_body_budget_preview_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_body_budget_preview_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/body"
    assert artifact["consumer"] == "future body/exercise/effective-budget activation slices"
    assert artifact["retirement_trigger"] == "approved body_exercise_budget_writeback_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["day_budget_ledger_mutated"] is False
    assert artifact["exercise_event_persisted"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["current_budget_view_refreshed"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_body_observation_preview_keeps_semantic_extraction_out_of_deterministic_code() -> None:
    cases = _by_id(build_body_budget_preview_contract_artifact())

    weight = cases["weight_observation_chat_preview"]
    assert weight["workflow_family"] == "body_observation"
    assert weight["normalized_handoff"] == "observation_create_candidate"
    assert weight["extraction_decision_mode"] == "llm_required_after_activation"
    assert weight["observation_write_authorized"] is False
    assert weight["active_body_plan_mutation_allowed"] is False
    assert weight["calibration_handoff_required_if_plan_change"] is True

    answer = cases["body_fat_answer_only_boundary"]
    assert answer["workflow_family"] == "general_chat"
    assert answer["disposition"] == "answer_only"
    assert answer["observation_write_authorized"] is False
    assert answer["body_plan_mutated"] is False


def test_exercise_previews_can_estimate_without_writeback_authority() -> None:
    cases = _by_id(build_body_budget_preview_contract_artifact())

    met = cases["exercise_met_estimate_preview"]
    assert met["workflow_family"] == "exercise"
    assert met["calculation_basis"] == "met_formula"
    assert met["estimated_kcal"] == 257
    assert met["ledger_write_authorized"] is False
    assert met["exercise_event_persisted"] is False
    assert met["ledger_entry_created"] is False

    asserted = cases["exercise_user_asserted_preview"]
    assert asserted["calculation_basis"] == "user_asserted"
    assert asserted["estimated_kcal"] == 320
    assert asserted["deterministic_formula_used"] is False
    assert asserted["ledger_write_authorized"] is False


def test_effective_budget_projection_stays_read_only_and_not_same_truth() -> None:
    projection = _by_id(build_body_budget_preview_contract_artifact())["effective_budget_what_if_projection"]

    assert projection["workflow_family"] == "budget_preview"
    assert projection["projection_only"] is True
    assert projection["current_budget_view_source_read_only"] is True
    assert projection["base_budget_kcal"] == 1800
    assert projection["consumed_kcal"] == 900
    assert projection["exercise_bonus_preview_kcal"] == 250
    assert projection["projected_effective_budget_kcal"] == 2050
    assert projection["projected_remaining_kcal"] == 1150
    assert projection["current_budget_view_refreshed"] is False


def test_preview_validator_rejects_runtime_or_mutation_drift() -> None:
    from app.body.application import body_budget_preview_contract as module

    artifact = build_body_budget_preview_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {**dict(cases[0]), "body_plan_mutated": True}
    cases[2] = {
        **dict(cases[2]),
        "exercise_event_persisted": True,
        "ledger_entry_created": True,
    }
    cases[4] = {**dict(cases[4]), "current_budget_view_refreshed": True}

    blockers = module._validate_cases(cases)

    assert "weight_observation_chat_preview.body_plan_mutated" in blockers
    assert "exercise_met_estimate_preview.exercise_event_persisted" in blockers
    assert "exercise_met_estimate_preview.ledger_entry_created" in blockers
    assert "effective_budget_what_if_projection.current_budget_view_refreshed" in blockers
