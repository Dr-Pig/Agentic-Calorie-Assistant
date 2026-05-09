from __future__ import annotations

from app.rescue.application.read_model_shadow_contract import (
    build_rescue_read_model_shadow_contract_artifact,
)


REQUIRED_CASES = [
    "active_inbox_projects_open_presented_negotiating_only",
    "history_keeps_dismissed_without_raw_trace",
    "non_rescue_proposals_filtered_from_rescue_views",
    "primary_actions_are_read_model_tokens_only",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_rescue_read_model_shadow_contract_is_offline_read_only() -> None:
    artifact = build_rescue_read_model_shadow_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_rescue_read_model_shadow_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/rescue"
    assert artifact["consumer"] == "future rescue accept/dismiss activation slices"
    assert artifact["retirement_trigger"] == "approved rescue_accept_dismiss_runtime_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["read_model_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["recommendation_posture_updated"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_active_inbox_projects_only_active_rescue_proposals() -> None:
    case = _by_id(build_rescue_read_model_shadow_contract_artifact())[
        "active_inbox_projects_open_presented_negotiating_only"
    ]

    assert case["active_inbox_ids"] == ["rescue-negotiating", "rescue-presented", "rescue-open"]
    assert case["dismissed_excluded_from_active_inbox"] is True
    assert case["sorted_newest_first"] is True
    assert case["raw_trace_exposed"] is False


def test_history_keeps_dismissed_without_exposing_raw_trace() -> None:
    case = _by_id(build_rescue_read_model_shadow_contract_artifact())[
        "history_keeps_dismissed_without_raw_trace"
    ]

    assert "rescue-dismissed" in case["history_ids"]
    assert case["dismissed_visible_in_history"] is True
    assert case["raw_trace_exposed"] is False
    assert case["expandable_explanation_available"] is True


def test_non_rescue_proposals_are_filtered_out() -> None:
    case = _by_id(build_rescue_read_model_shadow_contract_artifact())[
        "non_rescue_proposals_filtered_from_rescue_views"
    ]

    assert case["non_rescue_active_inbox_count"] == 0
    assert case["non_rescue_history_count"] == 0


def test_primary_actions_do_not_authorize_overlay_or_state_mutation() -> None:
    case = _by_id(build_rescue_read_model_shadow_contract_artifact())[
        "primary_actions_are_read_model_tokens_only"
    ]

    assert case["primary_actions"] == ["accept_rescue_plan", "dismiss_rescue_plan"]
    assert case["accept_action_commits_overlay"] is False
    assert case["dismiss_action_mutates_status"] is False
    assert case["ledger_entry_created"] is False
    assert case["proposal_committed"] is False


def test_shadow_contract_validator_rejects_runtime_or_mutation_drift() -> None:
    from app.rescue.application import read_model_shadow_contract as module

    artifact = build_rescue_read_model_shadow_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[3] = {
        **dict(cases[3]),
        "proposal_committed": True,
        "ledger_entry_created": True,
        "day_budget_mutated": True,
    }

    blockers = module._validate_cases(cases)

    assert "primary_actions_are_read_model_tokens_only.proposal_committed" in blockers
    assert "primary_actions_are_read_model_tokens_only.ledger_entry_created" in blockers
    assert "primary_actions_are_read_model_tokens_only.day_budget_mutated" in blockers
