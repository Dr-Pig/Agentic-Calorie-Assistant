from __future__ import annotations

from app.shared.contracts.bounded_react_loop import build_bounded_react_loop_contract


def test_bounded_react_loop_contract_declares_stop_reasons_and_round_limit() -> None:
    artifact = build_bounded_react_loop_contract()

    assert artifact["artifact_type"] == "bounded_react_loop_contract"
    assert artifact["status"] == "pass"
    assert artifact["orchestration_stance"] == "bounded_manager_react_loop"
    assert artifact["allowed_manager_actions"] == ["call_tools", "final"]
    assert artifact["max_rounds"] == 6
    assert artifact["stop_reasons"] == [
        "final_response_emitted",
        "tool_budget_exhausted",
        "repair_budget_exhausted",
        "guard_blocked",
    ]
    assert artifact["tool_results_return_to_manager_required"] is True
    assert artifact["pass1_pass2_is_subset_not_only_shape"] is True
