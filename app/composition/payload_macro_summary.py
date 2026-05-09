from __future__ import annotations

from typing import Any

from app.runtime.application.execution_guard import evaluate_macro_display


def _with_approved_trace(summary: dict[str, Any], trace_contract: dict[str, Any]) -> dict[str, Any]:
    approved_trace = trace_contract.get("approved_exact_macro_trace")
    if isinstance(approved_trace, dict):
        summary["approved_exact_macro_trace"] = approved_trace
    approved_fooddb_trace = trace_contract.get("approved_fooddb_evidence_trace")
    if isinstance(approved_fooddb_trace, dict):
        summary["approved_fooddb_evidence_trace"] = approved_fooddb_trace
    return summary


def build_payload_macro_summary(payload: Any | None) -> dict[str, Any]:
    if payload is None:
        return {"display_status": "hide", "guard_reason": "no_macro_data", "macro_kcal_delta": 0}

    display_macro = dict(getattr(payload, "display_macro_breakdown", None) or getattr(payload, "macro_breakdown", None) or {})
    trace_contract = dict(getattr(payload, "trace_contract", None) or {})
    if not display_macro:
        if trace_contract.get("macro_display_authorized") is False:
            return _with_approved_trace({
                "protein_g": int(getattr(payload, "protein_g", 0) or 0),
                "carbs_g": int(getattr(payload, "carb_g", 0) or 0),
                "fat_g": int(getattr(payload, "fat_g", 0) or 0),
                "display_status": "hide",
                "guard_reason": "no_macro_data",
                "macro_kcal": 0,
                "macro_kcal_delta": 0,
                "alignment_warning": False,
            }, trace_contract)
        display_macro = {
            "protein_g": int(getattr(payload, "protein_g", 0) or 0),
            "carb_g": int(getattr(payload, "carb_g", 0) or 0),
            "fat_g": int(getattr(payload, "fat_g", 0) or 0),
        }
    if not any(int(display_macro.get(key) or 0) > 0 for key in ("protein_g", "carb_g", "fat_g")):
        return _with_approved_trace({
            "protein_g": int(getattr(payload, "protein_g", 0) or 0),
            "carbs_g": int(getattr(payload, "carb_g", 0) or 0),
            "fat_g": int(getattr(payload, "fat_g", 0) or 0),
            "display_status": "hide",
            "guard_reason": "no_macro_data",
            "macro_kcal": 0,
            "macro_kcal_delta": 0,
            "alignment_warning": False,
        }, trace_contract)

    result = evaluate_macro_display(
        estimated_kcal=int(getattr(payload, "estimated_kcal", 0) or 0),
        protein_g=int(display_macro.get("protein_g") or 0),
        carb_g=int(display_macro.get("carb_g") or 0),
        fat_g=int(display_macro.get("fat_g") or 0),
    )
    return _with_approved_trace({
        "protein_g": int(display_macro.get("protein_g") or 0),
        "carbs_g": int(display_macro.get("carb_g") or 0),
        "fat_g": int(display_macro.get("fat_g") or 0),
        "display_status": result.display_status,
        "guard_reason": result.guard_reason,
        "macro_kcal": result.macro_kcal,
        "macro_kcal_delta": result.macro_kcal_delta,
        "alignment_warning": result.alignment_warning,
    }, trace_contract)
