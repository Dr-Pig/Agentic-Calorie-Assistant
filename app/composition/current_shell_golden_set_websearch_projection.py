from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_nutrition_projection import (
    first_nutrition_trace_contract,
    generic_range_evidence_present,
    macro_visible,
    visible_range_or_basis_present,
)


def attach_websearch_runtime_projection(
    runtime: dict[str, Any],
    nutrition_trace: dict[str, Any],
) -> None:
    web_trace = _dict(nutrition_trace.get("web_runtime_trace"))
    if not web_trace:
        return
    search_attempt_count = int(
        web_trace.get("search_attempt_count")
        or nutrition_trace.get("search_attempt_count")
        or 0
    )
    attempted = web_trace.get("attempted") is True or search_attempt_count > 0
    runtime.setdefault("websearch_tool_call_expected", attempted)
    if not attempted:
        return
    candidate_present = bool(web_trace.get("packetized_candidate_present")) or search_attempt_count > 0
    runtime.setdefault("websearch_candidate_only", candidate_present)
    runtime.setdefault("websearch_snippet_as_truth_allowed", False)
    runtime.setdefault("fooddb_truth_promotion_allowed", False)
    runtime.setdefault("pre_manager_websearch_routing_allowed", False)
    runtime.setdefault("websearch_candidate_to_commit_allowed", False)
    runtime.setdefault("websearch_candidate_to_macro_truth_allowed", False)
    runtime.setdefault("wrong_brand_promotion_allowed", False)
    runtime.setdefault("exact_promotion_allowed", False)
    runtime.setdefault("macro_truth_allowed", False)
    runtime.setdefault("source_truth_claim_allowed", False)
    runtime.setdefault("weak_generic_context_allowed", True)
    runtime.setdefault(
        "macro_visible_only_from_official_or_approved_evidence",
        str(runtime.get("macro_visibility_status") or "").startswith("hidden"),
    )


def attach_websearch_ui_projection(ui: dict[str, Any], request_trace: dict[str, Any]) -> None:
    nutrition_trace = first_nutrition_trace_contract(
        request_trace,
        _dict(request_trace.get("manager_final_decision")),
    )
    web_trace = _dict(nutrition_trace.get("web_runtime_trace"))
    search_attempt_count = int(
        web_trace.get("search_attempt_count")
        or nutrition_trace.get("search_attempt_count")
        or 0
    )
    attempted = web_trace.get("attempted") is True or search_attempt_count > 0
    if not attempted:
        if "generic_basis_visible" not in ui and generic_range_evidence_present(nutrition_trace):
            ui["generic_basis_visible"] = visible_range_or_basis_present(request_trace)
        return
    text = _visible_response_text(request_trace)
    ui.setdefault(
        "candidate_source_label_visible",
        _contains_any(text, ("候選", "資料", "來源", "外部", "查", "未核准", "還不能當作")),
    )
    ui.setdefault(
        "mismatch_warning_visible",
        _contains_any(text, ("不一致", "不同品牌", "不確定", "無法確認", "不是同一", "不足")),
    )
    ui.setdefault("macro_hidden_when_candidate_only", macro_visible(request_trace) is not True)
    ui.setdefault(
        "macro_source_status_visible",
        _contains_any(text, ("三大營養素", "蛋白", "碳水", "脂肪", "macro", "資料不足")),
    )


def _visible_response_text(request_trace: dict[str, Any]) -> str:
    renderer_output = _dict(request_trace.get("renderer_output"))
    text = str(renderer_output.get("assistant_message") or renderer_output.get("message") or "").strip()
    if text:
        return text
    manager_final = _dict(request_trace.get("manager_final_decision"))
    answer_contract = _dict(manager_final.get("answer_contract"))
    return str(
        answer_contract.get("reply_text")
        or answer_contract.get("text")
        or manager_final.get("response_summary")
        or ""
    ).strip()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
