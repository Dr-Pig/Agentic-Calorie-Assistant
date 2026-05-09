from __future__ import annotations

from app.body.application.calibration_proposal_boundary_contract import (
    build_calibration_proposal_boundary_contract_artifact,
)


REQUIRED_CASES = [
    "logging_quality_first_preview_no_plan_change",
    "budget_adjustment_preview_requires_stored_accept",
    "plan_reset_hidden_until_rescue_non_viable",
    "recent_open_proposal_blocks_new_proposal",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_calibration_boundary_contract_is_no_runtime_fixture_only() -> None:
    artifact = build_calibration_proposal_boundary_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_calibration_proposal_boundary_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/body"
    assert artifact["consumer"] == "future calibration runtime activation slices"
    assert artifact["retirement_trigger"] == "approved calibration_action_runtime_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["action_route_mounted"] is False
    assert artifact["proposal_container_created"] is False
    assert artifact["stored_action_applied"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["ledger_entry_created"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_logging_quality_first_preview_cannot_mutate_plan_or_ledger() -> None:
    case = _by_id(build_calibration_proposal_boundary_contract_artifact())[
        "logging_quality_first_preview_no_plan_change"
    ]

    assert case["proposal_family"] == "logging_quality_first"
    assert case["top_option_family"] == "logging_quality_first"
    assert case["plan_change_required"] is False
    assert case["requires_accept_before_plan_mutation"] is False
    assert case["plan_mutation_authorized"] is False
    assert case["ledger_mutation_authorized"] is False
    assert case["proposal_container_created"] is False


def test_budget_adjustment_preview_requires_stored_accept_not_raw_text_mutation() -> None:
    case = _by_id(build_calibration_proposal_boundary_contract_artifact())[
        "budget_adjustment_preview_requires_stored_accept"
    ]

    assert case["proposal_family"] == "budget_adjustment"
    assert case["top_option_family"] == "budget_adjustment"
    assert case["plan_change_required"] is True
    assert case["requires_accept_before_plan_mutation"] is True
    assert case["plan_mutation_authorized"] is False
    assert case["ledger_mutation_authorized"] is False
    assert case["accept_action_requires_proposal_container_id"] is True
    assert case["accept_action_raw_text_authorized_mutation"] is False
    assert case["stored_action_applied"] is False


def test_plan_reset_remains_hidden_alternative_until_rescue_is_non_viable() -> None:
    case = _by_id(build_calibration_proposal_boundary_contract_artifact())[
        "plan_reset_hidden_until_rescue_non_viable"
    ]

    assert case["rescue_recovery_viability"] == "non_viable"
    assert case["allowed_option_families"] == ["budget_adjustment", "pace_adjustment", "plan_reset"]
    assert case["primary_option_family"] == "budget_adjustment"
    assert case["plan_reset_default_visibility"] == "hidden_alternative"
    assert case["plan_mutation_authorized"] is False


def test_recent_open_proposal_blocks_new_calibration_proposal() -> None:
    case = _by_id(build_calibration_proposal_boundary_contract_artifact())[
        "recent_open_proposal_blocks_new_proposal"
    ]

    assert case["proposal_eligibility"] is False
    assert case["allowed_option_families"] == []
    assert case["blocked_reason_contains_open_proposal"] is True
    assert case["proposal_container_created"] is False


def test_boundary_validator_rejects_runtime_or_mutation_drift() -> None:
    from app.body.application import calibration_proposal_boundary_contract as module

    artifact = build_calibration_proposal_boundary_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[1] = {
        **dict(cases[1]),
        "action_route_mounted": True,
        "body_plan_mutated": True,
        "ledger_entry_created": True,
    }

    blockers = module._validate_cases(cases)

    assert "budget_adjustment_preview_requires_stored_accept.action_route_mounted" in blockers
    assert "budget_adjustment_preview_requires_stored_accept.body_plan_mutated" in blockers
    assert "budget_adjustment_preview_requires_stored_accept.ledger_entry_created" in blockers
