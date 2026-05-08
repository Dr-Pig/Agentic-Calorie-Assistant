from __future__ import annotations

import re
from typing import Any

from app.runtime.agent.manager import IntakeManagerResult


_INTERNAL_REPLY_LABELS = {
    "answer_only",
    "answer_remaining_budget",
    "onboarding_required",
    "read_only_state",
}
_CJK_DEGRADED_BUDGET_ZERO_RE = re.compile(
    r"(預算|目標|剩餘|還剩|可用)[^。！？!?，,；;:\n]{0,16}(0|零)\s*(卡路里|大卡|卡|kcal)?",
    re.IGNORECASE,
)
_EN_DEGRADED_BUDGET_ZERO_RE = re.compile(
    r"\b(budget|target|remaining|left|available)\b[^.\n,;:!?]{0,24}\b0\b"
    r"|\b0\b[^.\n,;:!?]{0,24}\b(budget|target|remaining|left|available)\b",
    re.IGNORECASE,
)


def build_degraded_budget_reply(
    manager_decision: IntakeManagerResult,
    remaining_budget: Any,
) -> tuple[str, str]:
    manager_reply = _reply_text_from_manager(manager_decision)
    if manager_reply and not contains_degraded_budget_zero_claim(manager_reply):
        return manager_reply, "manager_answer_contract"
    consumed = getattr(remaining_budget, "consumed_kcal", None)
    if isinstance(remaining_budget, dict):
        consumed = remaining_budget.get("consumed_kcal")
    try:
        consumed_kcal = int(consumed)
    except (TypeError, ValueError):
        return "尚未設定每日熱量目標；剩餘熱量要等完成設定後才能計算。", "safe_degraded_budget_fallback"
    return (
        f"尚未設定每日熱量目標；今天已記錄 {consumed_kcal} kcal，但剩餘熱量要等完成設定後才能計算。",
        "safe_degraded_budget_fallback",
    )


def contains_degraded_budget_zero_claim(text: str) -> bool:
    return bool(_CJK_DEGRADED_BUDGET_ZERO_RE.search(text) or _EN_DEGRADED_BUDGET_ZERO_RE.search(text))


def _reply_text_from_manager(manager_decision: IntakeManagerResult) -> str:
    answer_contract = getattr(manager_decision, "answer_contract", {})
    if not isinstance(answer_contract, dict):
        answer_contract = {}
    text = str(
        answer_contract.get("reply_text")
        or getattr(manager_decision, "response_summary", "")
        or ""
    ).strip()
    return "" if text.casefold() in _INTERNAL_REPLY_LABELS else text
