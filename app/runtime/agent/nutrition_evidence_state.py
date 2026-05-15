from __future__ import annotations

from typing import Any


def nutrition_evidence_present(tool_results: list[dict[str, Any]] | None) -> bool:
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool_name") or item.get("name") or "").strip()
        if name not in {"estimate_nutrition", "user_provided_kcal_evidence"} or item.get("failure_family"):
            continue
        evidence = item.get("evidence")
        if not isinstance(evidence, dict) or not isinstance(evidence.get("nutrition_payload"), dict):
            continue
        if name == "user_provided_kcal_evidence":
            trace_contract = dict(evidence["nutrition_payload"]).get("trace_contract")
            approved = dict(trace_contract.get("approved_user_provided_kcal_trace") or {}) if isinstance(trace_contract, dict) else {}
            if approved.get("runtime_truth_allowed") is True:
                return True
            continue
        return True
    return False
