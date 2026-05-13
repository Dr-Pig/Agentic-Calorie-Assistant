from __future__ import annotations

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
)
from app.runtime.contracts.manager import ManagerAction
from app.shared.contracts.manager_style_convergence import (
    BRANCH_DIVERGENCE_ALLOWED_ONLY_IN,
    FORBIDDEN_BRANCH_DIVERGENCE,
    HARNESS_SHAPES_ALLOWED,
    MANAGER_ACTIONS,
    ORCHESTRATION_STANCE,
    SHARED_TRUTH_OWNERS,
    build_shared_manager_style_convergence_contract,
)


def test_shared_manager_style_convergence_contract_has_one_runtime_stance() -> None:
    artifact = build_shared_manager_style_convergence_contract()

    assert artifact["artifact_type"] == "shared_manager_style_convergence_contract"
    assert artifact["status"] == "pass"
    assert artifact["orchestration_stance"] == ORCHESTRATION_STANCE
    assert artifact["manager_actions"] == list(MANAGER_ACTIONS)
    assert artifact["harness_shapes_allowed"] == list(HARNESS_SHAPES_ALLOWED)
    assert artifact["harness_shapes_are_not_product_architecture"] is True
    assert artifact["branch_divergence_allowed_only_in"] == list(
        BRANCH_DIVERGENCE_ALLOWED_ONLY_IN
    )
    assert artifact["forbidden_branch_divergence"] == list(
        FORBIDDEN_BRANCH_DIVERGENCE
    )
    assert artifact["shared_truth_owners"] == list(SHARED_TRUTH_OWNERS)
    assert artifact["one_manager_contract_required"] is True
    assert artifact["one_tool_vocabulary_required"] is True


def test_shared_manager_style_convergence_contract_matches_current_shell_actions() -> None:
    artifact = build_shared_manager_style_convergence_contract()

    assert artifact["manager_actions"] == [action.value for action in ManagerAction]


def test_advanced_product_lab_manager_registry_embeds_shared_convergence_contract() -> None:
    registry = build_product_lab_manager_tool_registry()
    convergence = registry["shared_manager_style_convergence"]

    assert registry["orchestration_stance"] == ORCHESTRATION_STANCE
    assert registry["manager_actions"] == list(MANAGER_ACTIONS)
    assert convergence["status"] == "pass"
    assert convergence["orchestration_stance"] == ORCHESTRATION_STANCE
    assert convergence["shared_truth_owners"] == list(SHARED_TRUTH_OWNERS)
    assert registry["tool_results_must_return_to_manager_pass"] is True
