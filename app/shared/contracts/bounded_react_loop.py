from __future__ import annotations

from typing import Any

from app.shared.contracts.manager_style_convergence import MANAGER_ACTIONS


def build_bounded_react_loop_contract() -> dict[str, Any]:
    return {
        "artifact_type": "bounded_react_loop_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "orchestration_stance": "bounded_manager_react_loop",
        "allowed_manager_actions": list(MANAGER_ACTIONS),
        "max_rounds": 6,
        "stop_reasons": [
            "final_response_emitted",
            "tool_budget_exhausted",
            "repair_budget_exhausted",
            "guard_blocked",
        ],
        "tool_results_return_to_manager_required": True,
        "pass1_pass2_is_subset_not_only_shape": True,
        "blockers": [],
    }


__all__ = ["build_bounded_react_loop_contract"]
