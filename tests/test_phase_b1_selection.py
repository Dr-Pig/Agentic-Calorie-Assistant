from __future__ import annotations

import inspect

from app.runtime.agent.manager_branch_constraints import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
)
from app.runtime.agent.phase_b1_selection import (
    NATURAL_MODE,
    PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
    PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID,
    select_phase_b1_profile_route,
    select_phase_b1_task_payload,
)


def test_phase_b1_task_payload_selector_is_raw_state_only() -> None:
    signature = inspect.signature(select_phase_b1_task_payload)

    assert "raw_user_input" not in signature.parameters
    assert "case_family" in signature.parameters
    assert "manager_role" in signature.parameters
    assert "probe_mode" in signature.parameters


def test_phase_b1_profile_route_selector_keeps_caller_free_of_artifact_basis_wiring() -> None:
    signature = inspect.signature(select_phase_b1_profile_route)

    assert "b1003_artifact_basis" not in signature.parameters
    assert "b1005_artifact_basis" not in signature.parameters
    assert "b1006_artifact_basis" not in signature.parameters
    assert "case_set" in signature.parameters
    assert "case_family" in signature.parameters
    assert "case_id" in signature.parameters


def test_phase_b1_pass2_clarify_only_selection_exposes_contract_metadata() -> None:
    selection = select_phase_b1_task_payload(
        manager_role="pass_2_synthesis",
        probe_mode=NATURAL_MODE,
        case_family=B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    )

    assert selection.task_payload_id == PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID
    assert selection.constraint_id == "phase_b1_pass2_clarify_only_contract_v1"
    assert selection.schema_branch == "pass2_clarify_only"
    assert selection.guidance_fragment_id == "b1_004_clarify_only_json_first_v1"
    assert "manager_action" in selection.allowed_fields
    assert "answer_contract" in selection.allowed_fields
    assert "mutation_result" in selection.forbidden_fields
    assert selection.uses_case_id_local_debt is False


def test_phase_b1_pass1_listed_ingredient_selection_keeps_shared_payload_with_specific_contract() -> None:
    selection = select_phase_b1_task_payload(
        manager_role="pass_1_tool_request",
        probe_mode=NATURAL_MODE,
        case_family=B1_LISTED_INGREDIENT_CASE_FAMILY,
    )

    assert selection.task_payload_id == PHASE_B1_PASS_1_NATURAL_FALLBACK_ID
    assert selection.constraint_id == "phase_b1_pass1_listed_ingredient_tool_call_contract_v1"
    assert selection.schema_branch == "pass1_listed_ingredient_tool_call"
    assert selection.guidance_fragment_id == "listed_ingredient_json_first_tool_request_v1"
    assert "tool_calls" in selection.allowed_fields
    assert "item_results" in selection.forbidden_fields
    assert selection.uses_case_id_local_debt is False


def test_phase_b1_full_smoke_b1005_route_marks_case_id_local_debt() -> None:
    selection = select_phase_b1_profile_route(
        case_set="full",
        requested_profile_id=None,
        probe_mode=NATURAL_MODE,
        manager_role="pass_1_tool_request",
        case_id="B1-005",
        case_family=B1_LISTED_INGREDIENT_CASE_FAMILY,
        selected_profile_id="builderspace-deepseek-default",
        default_profile_id="builderspace-deepseek-default",
        profile_applies=True,
    )

    assert selection.profile_id == "builderspace-grok-4-fast-b1005-probe"
    assert selection.route_mode == "auto_branch_route"
    assert selection.route_rule_id == "phase_b1_full_smoke_b1005_pass1_grok_route_v1"
    assert selection.route_scope == "b1_local_diagnostic"
    assert selection.artifact_basis == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T180042.469158Z_natural-probe_targeted_B1-005_b176c8.json",
        "observed_result": "B1-005_pass1_grok_item_level_lookup_generic_food",
        "prior_default_failure": "B1-005_pass1_deepseek_search_tool_policy_mismatch",
    }
    assert selection.uses_case_id_local_debt is True
    assert selection.should_migrate_post_b1 is True


def test_phase_b1_full_smoke_b1003_route_stays_family_scoped_local_diagnostic_rule() -> None:
    selection = select_phase_b1_profile_route(
        case_set="full",
        requested_profile_id=None,
        probe_mode=NATURAL_MODE,
        manager_role="pass_1_tool_request",
        case_id="B1-003",
        case_family=B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        selected_profile_id="builderspace-deepseek-default",
        default_profile_id="builderspace-deepseek-default",
        profile_applies=True,
    )

    assert selection.profile_id == "builderspace-grok-4-fast-b1003-probe"
    assert selection.route_mode == "auto_branch_route"
    assert selection.route_rule_id == "phase_b1_full_smoke_b1003_pass1_grok_route_v1"
    assert selection.route_scope == "b1_local_diagnostic"
    assert selection.artifact_basis == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T155117.987328Z_natural-probe_targeted_B1-003_4ab12d.json",
        "observed_result": "B1-003_pass1_grok_legal_decision",
        "prior_default_failure": "B1-003_pass1_deepseek_tool_call_transport_contract_breach",
    }
    assert selection.uses_case_id_local_debt is False
    assert selection.should_migrate_post_b1 is True


def test_phase_b1_full_smoke_b1006_route_keeps_case_id_local_debt_inside_local_registry() -> None:
    selection = select_phase_b1_profile_route(
        case_set="full",
        requested_profile_id=None,
        probe_mode=NATURAL_MODE,
        manager_role="pass_1_tool_request",
        case_id="B1-006",
        case_family=B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        selected_profile_id="builderspace-deepseek-default",
        default_profile_id="builderspace-deepseek-default",
        profile_applies=True,
    )

    assert selection.profile_id == "builderspace-grok-4-fast-b1006-probe"
    assert selection.route_mode == "auto_branch_route"
    assert selection.route_rule_id == "phase_b1_full_smoke_b1006_pass1_grok_route_v1"
    assert selection.route_scope == "b1_local_diagnostic"
    assert selection.artifact_basis == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T172310.969052Z_natural-probe_targeted_B1-006_242ece.json",
        "observed_result": "B1-006_pass1_grok_legal_decision",
        "prior_default_failure": "B1-006_pass1_deepseek_non_json_model_output",
    }
    assert selection.uses_case_id_local_debt is True
    assert selection.should_migrate_post_b1 is True
