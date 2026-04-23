from __future__ import annotations

from typing import Any


def build_deterministic_sidecar(
    *,
    active_body_plan_view: Any,
    current_budget_view: Any,
    state_mutation_summary: dict[str, Any],
    trace_summary: dict[str, Any],
    overshoot_summary: dict[str, Any] | None = None,
    macro_summary: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body_plan = active_body_plan_view.model_dump(mode="json")
    today = current_budget_view.model_dump(mode="json")
    macro = dict(macro_summary or {})
    if body_plan.get("body_plan_id") is None:
        today["budget_kcal"] = 0
        today["remaining_kcal"] = 0
        today["adjustment_kcal"] = 0
    macro["protein_g"] = int(today.get("consumed_protein") or 0)
    macro["carbs_g"] = int(today.get("consumed_carbs") or 0)
    macro["fat_g"] = int(today.get("consumed_fat") or 0)
    macro["display_status"] = "show" if bool(today.get("show_macro")) else "hide"
    macro["guard_reason"] = str(today.get("macro_guard_reason") or macro.get("guard_reason") or "macro_missing")
    macro.setdefault("macro_kcal_delta", 0)
    return {
        "ui": {
            "body_plan": body_plan,
            "today": today,
        },
        "overshoot": overshoot_summary or {
            "overshoot_detected": False,
            "overshoot_kcal": 0,
        },
        "macro": macro or {
            "display_status": "hide",
            "guard_reason": "macro_missing",
            "macro_kcal_delta": 0,
        },
        "evidence": evidence_summary or {
            "eligibility": "unknown",
            "why_not_exact": [],
            "high_variance_family": False,
        },
        "state_mutation_summary": state_mutation_summary,
        "trace_summary": trace_summary,
    }
