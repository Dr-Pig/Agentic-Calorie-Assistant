from __future__ import annotations

from typing import Any


def browser_entrypoint_blockers(result: dict[str, Any], case: dict[str, Any]) -> list[str]:
    if str(case.get("entrypoint") or "") != "browser_ui":
        return []
    ui = dict(result.get("ui") or {})
    if ui.get("browser_executed") is True:
        return []
    return ["ui.browser_executed_not_true_for_browser_case"]


def dogfood_trace_blockers(result: dict[str, Any], case: dict[str, Any]) -> list[str]:
    trace = dict(result.get("dogfood_trace") or {})
    expected = dict(case.get("dogfood_trace") or {})
    blockers: list[str] = []
    if expected.get("trace_id_required") is True and not str(trace.get("trace_id") or "").strip():
        blockers.append("dogfood_trace.trace_id_missing")
    if expected.get("feedback_links_to_trace") is True and trace.get("feedback_links_to_trace") is not True:
        blockers.append("dogfood_trace.feedback_links_to_trace_not_true")
    if str(case.get("case_id") or "") == "GS17":
        if not str(trace.get("feedback_record_id") or "").strip():
            blockers.append("dogfood_trace.feedback_record_id_missing")
        if trace.get("feedback_linkage_source") != "feedback_record":
            blockers.append("dogfood_trace.feedback_linkage_source_not_feedback_record")
        for field in ("auto_attaches_recent_messages", "auto_attaches_read_model_snapshot"):
            if expected.get(field) is True and trace.get(field) is not True:
                blockers.append(f"dogfood_trace.{field}_not_true")
    if (
        expected.get("correlates_ui_runtime_read_model_response") is True
        and trace.get("correlates_ui_runtime_read_model_response") is not True
    ):
        blockers.append("dogfood_trace.correlates_ui_runtime_read_model_response_not_true")
    return blockers
