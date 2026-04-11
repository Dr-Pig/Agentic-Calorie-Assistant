from __future__ import annotations

from typing import Any


HIGH_IMPACT_SLOT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "brand": ("品牌", "哪家", "哪一間", "摩斯", "麥當勞", "星巴克", "7-11", "全家"),
    "size": ("大杯", "中杯", "小杯", "杯型", "尺寸", "大小", "碗大小", "份量"),
    "portion": ("幾份", "幾碗", "幾顆", "多少", "份量", "吃多少"),
    "main_items": ("哪些食材", "哪些料", "主菜", "內容物", "吃了什麼", "哪些滷味"),
    "base_or_sauce": ("底", "飯", "麵", "醬", "醬汁", "醬料"),
}


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _classify_slot(text: str) -> str:
    lowered = text.lower()
    for slot_name, keywords in HIGH_IMPACT_SLOT_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return slot_name
    return "other"


def derive_missing_high_impact_slots(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for value in reasoning_state.get("missing_high_impact_slots") or []:
        candidates.append(str(value))
    for value in parsed.get("missing_slots") or []:
        candidates.append(str(value))
    for value in parsed.get("blocking_slots") or []:
        candidates.append(str(value))
    for value in parsed.get("unresolved_info") or []:
        candidates.append(str(value))
    return _dedupe_preserve([item for item in candidates if _classify_slot(item) != "other"])


def derive_followup_targets(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for item in derive_missing_high_impact_slots(parsed, reasoning_state):
        slot_name = _classify_slot(item)
        if slot_name != "other":
            targets.append(slot_name)
    question = str(parsed.get("followup_question") or "").strip()
    if question:
        for slot_name, keywords in HIGH_IMPACT_SLOT_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                targets.append(slot_name)
    return _dedupe_preserve(targets)


def classify_followup_decision(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> str:
    question = str(parsed.get("followup_question") or "").strip()
    if not question and not bool(parsed.get("follow_up_needed")):
        return "direct_answer"
    estimated_kcal = int(parsed.get("estimated_kcal") or 0)
    missing_targets = derive_followup_targets(parsed, reasoning_state)
    if estimated_kcal > 0 and (missing_targets or question):
        return "estimate_with_followup"
    return "ask_followup_only"


def annotate_followup_policy(parsed: dict[str, Any]) -> dict[str, Any]:
    reasoning_state = dict(parsed.get("reasoning_state") or {})
    missing_high_impact_slots = derive_missing_high_impact_slots(parsed, reasoning_state)
    followup_targets = derive_followup_targets(parsed, reasoning_state)
    followup_decision = classify_followup_decision(parsed, reasoning_state)
    why_followup = str(parsed.get("follow_up_reasoning") or "").strip()
    if not why_followup and followup_decision != "direct_answer":
        why_followup = "high_impact_slot_missing" if missing_high_impact_slots else "needs_refinement"
    reason_not_direct_answer = str(parsed.get("reason_not_direct_answer") or "").strip()
    if not reason_not_direct_answer and followup_decision != "direct_answer":
        reason_not_direct_answer = why_followup or "missing_high_impact_slot"
    return {
        **parsed,
        "missing_high_impact_slots": missing_high_impact_slots,
        "followup_targets": followup_targets,
        "followup_decision_type": followup_decision,
        "why_followup": why_followup,
        "reason_not_direct_answer": reason_not_direct_answer,
    }


def annotate_cannot_estimate_abstain_policy(parsed: dict[str, Any]) -> dict[str, Any]:
    resolution_mode = str(parsed.get("resolution_mode") or "").strip()
    if resolution_mode != "cannot_estimate_yet":
        return parsed

    updated = dict(parsed)
    canonical_write_decision = dict(updated.get("canonical_write_decision") or {})
    canonical_write_decision.update(
        {
            "mode": "abstain",
            "can_write_canonical": False,
            "reason": "cannot_estimate_yet",
        }
    )
    updated["canonical_write_decision"] = canonical_write_decision
    updated["follow_up_needed"] = True
    updated["response_mode_hint"] = "clarify_first"
    updated["action_taken"] = "clarify_before_estimate"
    if not str(updated.get("follow_up_reasoning") or "").strip():
        updated["follow_up_reasoning"] = "Nutrition resolution could not safely estimate."
    unresolved_info = [str(item).strip() for item in updated.get("unresolved_info", []) if str(item).strip()]
    if "cannot_estimate_yet" not in unresolved_info:
        unresolved_info.insert(0, "cannot_estimate_yet")
    updated["unresolved_info"] = unresolved_info
    return annotate_followup_policy(updated)
