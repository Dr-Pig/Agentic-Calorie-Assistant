from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_nutrition_projection import (
    component_basis_present,
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
    runtime.setdefault("search_candidate_packet_truth_allowed", False)
    runtime.setdefault("websearch_snippet_as_truth_allowed", False)
    runtime.setdefault("fooddb_truth_promotion_allowed", False)
    runtime.setdefault("permanent_fooddb_promotion_allowed", False)
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
    source_status = str(web_trace.get("source_admissibility_status") or "").strip().lower()
    selected_extract_present = web_trace.get("selected_extract_present") is True
    turn_packet_present = web_trace.get("turn_web_evidence_packet_present") is True
    if source_status == "accepted" or selected_extract_present or turn_packet_present:
        runtime.setdefault("selected_extract_required", selected_extract_present or turn_packet_present)
        runtime.setdefault("source_admissibility_required", source_status == "accepted")
        runtime.setdefault("turn_web_evidence_packet_allowed", turn_packet_present)
        runtime.setdefault(
            "turn_web_evidence_may_support_commit",
            web_trace.get("turn_web_evidence_may_support_commit") is True,
        )
    if source_status in {"rejected", "downgraded"} or web_trace.get("wrong_context_source_rejected") is True:
        runtime.setdefault("wrong_context_source_rejected", True)
        runtime.setdefault("selected_extract_required", False)
        runtime.setdefault("turn_web_evidence_packet_allowed", False)
        runtime.setdefault("runtime_mutation_allowed", False)
    if web_trace.get("component_level_evidence_present") is True:
        runtime.setdefault("component_level_evidence_required", True)
        runtime.setdefault("generic_combo_black_box_allowed", False)
        runtime.setdefault("each_component_source_required", True)


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
    ui.setdefault("candidate_source_label_visible", _source_label_visible(text))
    ui.setdefault("mismatch_warning_visible", _mismatch_warning_visible(text))
    if web_trace.get("turn_web_evidence_packet_present") is True:
        ui.setdefault(
            "turn_web_evidence_source_visible",
            _contains_any(text, ("來源", "依", "evidence", "source", "kcal", "卡")),
        )
    if web_trace.get("component_level_evidence_present") is True:
        ui.setdefault(
            "component_basis_visible",
            component_basis_present(request_trace) is True
            and _contains_any(text, ("組件", "component", "大麥克", "中薯", "可樂", "來源")),
        )
    ui.setdefault("macro_hidden_when_candidate_only", macro_visible(request_trace) is not True)
    ui.setdefault(
        "macro_source_status_visible",
        _contains_any(
            text,
            ("三大營養素", "營養素", "資料不足", "不顯示", "macro", "missing"),
        ),
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


def _source_label_visible(text: str) -> bool:
    return _contains_any(
        text,
        (
            "來源",
            "查到",
            "資料",
            "證據",
            "官方",
            "候選",
            "source",
            "evidence",
        ),
    )


def _mismatch_warning_visible(text: str) -> bool:
    return _contains_any(
        text,
        (
            "冷凍",
            "電商",
            "包裝",
            "不適合",
            "不符合",
            "不當作",
            "不採用",
            "not applicable",
            "wrong context",
            "mismatch",
            "rejected",
        ),
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
