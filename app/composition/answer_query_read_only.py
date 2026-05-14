from __future__ import annotations

import re
from typing import Any

from app.runtime.agent.manager import IntakeManagerResult


_MACRO_GRAM_SENTENCE_RE = re.compile(
    r"[^。\n]*(?:蛋白質|碳水|脂肪)[^。\n]*\d+\s*g[^。\n]*(?:。|$)"
    r"|[^.\n]*(?:protein|carb|carbs|fat)[^.\n]*\d+\s*g[^.\n]*(?:\.|$)",
    re.IGNORECASE,
)


def finalize_answer_query_read_only(
    *,
    manager_decision: IntakeManagerResult,
    request_id: str,
    append_trace_event: Any,
) -> dict[str, Any] | None:
    if not _is_answer_query_no_mutation(manager_decision):
        return None
    assistant_message_override = _sanitize_answer_query_reply_text(
        manager_decision.answer_contract.get("reply_text")
        or manager_decision.response_summary
        or "",
        answer_contract=manager_decision.answer_contract,
    ) or None
    append_trace_event(
        request_id=request_id,
        stage="v2_answer_query_read_only",
        status="ok",
        summary={
            "workflow_effect": manager_decision.workflow_effect,
            "intent_type": manager_decision.intent_type,
            "state_mutation": "none",
        },
    )
    return {
        "remaining_budget": None,
        "assistant_message_override": assistant_message_override,
    }


def _is_answer_query_no_mutation(manager_decision: IntakeManagerResult) -> bool:
    return (
        getattr(manager_decision, "intent_type", "") == "answer_query"
        and getattr(manager_decision, "workflow_effect", "") == "answer_only"
        and getattr(manager_decision, "final_action", "") == "answer_only"
        and not getattr(manager_decision, "tool_calls", ())
    )


def _sanitize_answer_query_reply_text(reply_text: Any, *, answer_contract: dict[str, Any] | None = None) -> str:
    text = str(reply_text or "").strip()
    if not text:
        return ""
    text = re.sub(r"[（(]\s*rough\s+estimate\s*[）)]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brough\s+estimate\b", "粗估", text, flags=re.IGNORECASE)
    replacements = {
        "rough_estimate_without_source": "粗估、沒有明確資料來源",
        "unverified_estimate": "未驗證估計",
        "llm_only": "粗估、沒有明確資料來源",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    if not _answer_contract_allows_visible_macros(answer_contract):
        text = _MACRO_GRAM_SENTENCE_RE.sub("三大營養素資料不足，先不顯示。", text)
    return " ".join(text.split())


def _answer_contract_allows_visible_macros(answer_contract: dict[str, Any] | None) -> bool:
    if not isinstance(answer_contract, dict):
        return False
    basis = answer_contract.get("answer_basis")
    if isinstance(basis, dict):
        visibility = str(basis.get("macro_visibility_status") or "").lower()
        return visibility in {"visible", "present", "show"}
    lowered = str(basis or "").lower()
    return "macro_visibility_status='visible'" in lowered or "macro_visibility_status=visible" in lowered


__all__ = ["finalize_answer_query_read_only"]
