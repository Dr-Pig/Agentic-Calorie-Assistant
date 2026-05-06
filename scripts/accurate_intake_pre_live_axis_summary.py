from __future__ import annotations

from typing import Any


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary")
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_capability_axis_summary(
    evidence_status: dict[str, dict[str, Any]],
    *,
    selected_option: str,
    ready_for_pl_ce_local_review: bool,
) -> dict[str, Any]:
    browser = evidence_status["browser_shell_smoke"]
    manager_intent = evidence_status["manager_intent_readiness_review_pack"]
    manager_summary = _summary(manager_intent)
    context_gate = evidence_status["context_live_diagnostic_gate"]
    context_gate_summary = _summary(context_gate)
    live_invoked = (
        context_gate.get("live_llm_invoked") is True
        or context_gate.get("live_provider_invoked") is True
    )
    gate_status = str(context_gate.get("status") or "")
    if gate_status == "context_live_diagnostic_gate_ready_without_live_canary":
        context_live_status = "pre_live_ready_without_live_canary"
    elif live_invoked:
        context_live_status = "live_diagnostic_seen_not_pre_live_gate"
    else:
        context_live_status = "blocked_or_missing"
    return {
        "browser_execution": {
            "status": (
                "pass"
                if browser.get("status") == "pass" and browser.get("browser_executed") is True
                else "blocked_or_missing"
            ),
            "browser_executed": browser.get("browser_executed") is True,
        },
        "product_loop_context_review": {
            "status": "ready_for_human_review" if ready_for_pl_ce_local_review else "blocked_or_missing",
            "ready_for_pl_ce_local_review": ready_for_pl_ce_local_review,
        },
        "manager_intent_readiness": {
            "status": (
                "ready_for_human_review"
                if manager_intent.get("status")
                == "manager_intent_readiness_ready_for_human_review"
                else "blocked_or_missing"
            ),
            "semantic_owner": manager_intent.get("semantic_owner") or "not_available",
            "context_known_runtime_gaps": _int_value(
                manager_summary.get("context_known_runtime_gaps")
            ),
        },
        "context_live_diagnostic": {
            "status": context_live_status,
            "live_stage": (
                "not_invoked" if not live_invoked else str(context_gate.get("live_stage") or "unknown")
            ),
            "live_provider_output_count": _int_value(
                context_gate_summary.get("live_provider_output_count")
            ),
            "live_blocked_response_count": _int_value(
                context_gate_summary.get("live_blocked_response_count")
            ),
            "anti_overfit_guard": str(
                evidence_status["context_live_diagnostic_anti_overfit_guard"].get("status")
                or "missing"
            ),
            "holdout_plan": str(
                evidence_status["context_live_diagnostic_holdout_plan"].get("status")
                or "missing"
            ),
            "response_contract_dry_run": str(
                evidence_status["context_live_response_contract_dry_run"].get("status")
                or "missing"
            ),
        },
        "fooddb_dependency": {
            "status": "blocked_out_of_scope_waiting_fooddb_artifact",
            "ready_for_fdb_integration": False,
        },
        "final_e2e_dependency": {
            "status": "blocked_until_fooddb_and_live_manager_integration",
            "selected_option": selected_option,
        },
    }


__all__ = ["build_capability_axis_summary"]
