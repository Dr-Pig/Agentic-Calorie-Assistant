from __future__ import annotations

from typing import Any


def build_today_macro_runtime_summary_flags(
    base_gate: dict[str, Any],
    missing_payload_fields: list[str],
) -> dict[str, bool]:
    base_summary = dict(base_gate.get("summary") or {})
    guarded_case = dict(base_gate.get("guarded_case") or {})
    return {
        "macro_visible_case_checked": base_summary.get("visible_case_checked") is True,
        "macro_guarded_case_checked": base_summary.get("guarded_case_checked") is True,
        "backend_macro_fields_required": not missing_payload_fields,
        "show_macro_false_suppresses_macro": (
            guarded_case.get("macro_state") == "guarded"
            and guarded_case.get("macro_grid_hidden") is True
            and guarded_case.get("macro_guard_reason_hidden") is False
            and guarded_case.get("protein_text") == "--"
            and guarded_case.get("carbs_text") == "--"
            and guarded_case.get("fat_text") == "--"
        ),
    }


__all__ = ["build_today_macro_runtime_summary_flags"]
