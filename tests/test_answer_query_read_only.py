from __future__ import annotations

from typing import Any

from app.composition.answer_query_read_only import finalize_answer_query_read_only
from app.runtime.agent.manager_result_builder import IntakeManagerResult


def test_answer_query_read_only_sanitizes_internal_estimate_labels_and_unsupported_macros() -> None:
    trace_events: list[dict[str, Any]] = []
    result = finalize_answer_query_read_only(
        manager_decision=IntakeManagerResult(
            intent="estimate basis",
            manager_action="final",
            final_action="answer_only",
            workflow_effect="answer_only",
            intent_type="answer_query",
            answer_contract={
                "reply_text": (
                    "這是粗略估計（rough estimate）。"
                    "蛋白質約18g、碳水42g、脂肪12g。"
                    "來源是 rough_estimate_without_source。"
                ),
                "answer_basis": "macro_visibility_status='hidden_missing_source'",
                "references_active_meal": True,
            },
        ),
        request_id="req-1",
        append_trace_event=lambda **event: trace_events.append(event),
    )

    assert result is not None
    reply = result["assistant_message_override"]
    assert "rough estimate" not in reply
    assert "rough_estimate_without_source" not in reply
    assert "蛋白質約18g" not in reply
    assert "三大營養素資料不足" in reply
    assert trace_events[0]["stage"] == "v2_answer_query_read_only"


def test_answer_query_read_only_keeps_explicit_visible_macro_reply() -> None:
    result = finalize_answer_query_read_only(
        manager_decision=IntakeManagerResult(
            intent="estimate basis",
            manager_action="final",
            final_action="answer_only",
            workflow_effect="answer_only",
            intent_type="answer_query",
            answer_contract={
                "reply_text": "這筆有標示資料：蛋白質12g、碳水48g、脂肪6g。",
                "answer_basis": {"macro_visibility_status": "visible"},
                "references_active_meal": True,
            },
        ),
        request_id="req-1",
        append_trace_event=lambda **_: None,
    )

    assert result is not None
    assert result["assistant_message_override"] == "這筆有標示資料：蛋白質12g、碳水48g、脂肪6g。"


def test_answer_query_read_only_keeps_macro_insufficient_sentence_without_grams() -> None:
    result = finalize_answer_query_read_only(
        manager_decision=IntakeManagerResult(
            intent="estimate basis",
            manager_action="final",
            final_action="answer_only",
            workflow_effect="answer_only",
            intent_type="answer_query",
            answer_contract={
                "reply_text": "宏量營養（如蛋白質、碳水、脂肪）資料不足，無法提供具體克數。",
                "answer_basis": "macro_visibility_status='hidden_missing_source'",
                "references_active_meal": True,
            },
        ),
        request_id="req-1",
        append_trace_event=lambda **_: None,
    )

    assert result is not None
    assert result["assistant_message_override"] == "宏量營養（如蛋白質、碳水、脂肪）資料不足，無法提供具體克數。"
