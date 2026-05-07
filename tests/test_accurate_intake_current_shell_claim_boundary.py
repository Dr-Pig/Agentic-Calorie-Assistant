from __future__ import annotations

from app.composition.accurate_intake_current_shell_claim_boundary import (
    build_current_shell_appshell_claim_boundary,
)


def test_current_shell_appshell_claim_boundary_reads_repo_truth_and_gate_dependencies() -> None:
    boundary = build_current_shell_appshell_claim_boundary()

    assert boundary["launch_scope"] == "current_shell_v1"
    assert boundary["current_shell_sync_contract_source"] == "docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml"
    assert (
        boundary["manager_runtime_gate_ledger_source"]
        == "docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml"
    )
    assert boundary["current_shell_in_scope_journeys"] == ["A", "B", "C", "D", "E", "G", "H", "J", "K"]
    assert boundary["appshell_rules"]["static_contract_fixture_may_queue_without_runtime_gate"] is True
    assert boundary["appshell_rules"]["runtime_backed_requires_upstream_gate_green"] is True
    assert boundary["appshell_rules"]["browser_executed_requires_upstream_gate_green"] is True
    assert boundary["required_manager_runtime_gates"]
    assert set(boundary["green_manager_runtime_gates"]).issubset(
        set(boundary["required_manager_runtime_gates"])
    )
    assert set(boundary["non_green_manager_runtime_gates"]).issubset(
        set(boundary["required_manager_runtime_gates"])
    )
    assert set(boundary["green_manager_runtime_gates"]).isdisjoint(
        set(boundary["non_green_manager_runtime_gates"])
    )


def test_current_shell_appshell_claim_boundary_claim_readiness_tracks_non_green_runtime_gates() -> None:
    boundary = build_current_shell_appshell_claim_boundary()
    blocked = bool(boundary["non_green_manager_runtime_gates"])

    assert boundary["runtime_backed_claim_ready"] is (not blocked)
    assert boundary["browser_executed_claim_ready"] is (not blocked)
    expected_status = (
        "ready_for_runtime_and_browser_claims"
        if not blocked
        else "blocked_on_manager_runtime_upstream_gates"
    )
    assert boundary["status"] == expected_status
    assert set(boundary["manager_runtime_gate_statuses"]) == set(
        boundary["required_manager_runtime_gates"]
    )
