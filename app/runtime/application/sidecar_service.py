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
    macro_summary_supplied = bool(macro)
    if not macro:
        macro = {
            "macro_kcal_delta": 0,
        }
    else:
        macro.setdefault("macro_kcal_delta", 0)
    today_display_status = "show" if bool(today.get("show_macro")) else "hide"
    summary_display_status = str(macro.get("display_status") or today_display_status)
    display_status = "show" if today_display_status == "show" and summary_display_status == "show" else "hide"
    if macro_summary_supplied and summary_display_status == "hide":
        guard_reason = str(macro.get("guard_reason") or "no_macro_data")
        protein_g = int(macro.get("protein_g") or 0)
        carbs_g = int(macro.get("carbs_g") or 0)
        fat_g = int(macro.get("fat_g") or 0)
    else:
        guard_reason = (
            str(today.get("macro_guard_reason") or "no_macro_data")
            if today_display_status == "hide"
            else str(macro.get("guard_reason") or today.get("macro_guard_reason") or "no_macro_data")
        )
        protein_g = int(
            macro.get("protein_g")
            if macro.get("protein_g") is not None
            else today.get("consumed_protein") or 0
        )
        carbs_g = int(
            macro.get("carbs_g")
            if macro.get("carbs_g") is not None
            else today.get("consumed_carbs") or 0
        )
        fat_g = int(
            macro.get("fat_g")
            if macro.get("fat_g") is not None
            else today.get("consumed_fat") or 0
        )
    macro.update(
        {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "display_status": display_status,
            "guard_reason": guard_reason,
        }
    )
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
            "guard_reason": "no_macro_data",
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
