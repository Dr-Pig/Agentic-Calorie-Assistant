from __future__ import annotations

from typing import Any


FOLLOWUP_DECISION_TYPES = {"direct_answer", "estimate_with_followup", "ask_followup_only"}


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


def _structured_values(mapping: dict[str, Any], key: str) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def derive_missing_high_impact_slots(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    candidates.extend(_structured_values(reasoning_state, "missing_high_impact_slots"))
    candidates.extend(_structured_values(parsed, "missing_high_impact_slots"))
    candidates.extend(_structured_values(parsed, "missing_slots"))
    candidates.extend(_structured_values(parsed, "blocking_slots"))
    return _dedupe_preserve(candidates)


def derive_followup_targets(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    candidates.extend(_structured_values(reasoning_state, "followup_targets"))
    candidates.extend(_structured_values(parsed, "followup_targets"))
    candidates.extend(derive_missing_high_impact_slots(parsed, reasoning_state))
    return _dedupe_preserve(candidates)


def classify_followup_decision(parsed: dict[str, Any], reasoning_state: dict[str, Any]) -> str:
    explicit = str(
        parsed.get("followup_decision_type")
        or reasoning_state.get("followup_decision_type")
        or reasoning_state.get("followup_policy_decision")
        or ""
    ).strip()
    if explicit in FOLLOWUP_DECISION_TYPES:
        return explicit

    response_mode_hint = str(parsed.get("response_mode_hint") or "").strip()
    action_taken = str(parsed.get("action_taken") or "").strip()
    if response_mode_hint == "clarify_first" or action_taken == "clarify_before_estimate":
        return "ask_followup_only"

    estimated_kcal = int(parsed.get("estimated_kcal") or 0)
    manager_followup_present = bool(parsed.get("follow_up_needed"))
    if estimated_kcal > 0 and manager_followup_present:
        return "estimate_with_followup"
    return "direct_answer"


def annotate_followup_policy(parsed: dict[str, Any]) -> dict[str, Any]:
    reasoning_state = dict(parsed.get("reasoning_state") or {})
    missing_high_impact_slots = derive_missing_high_impact_slots(parsed, reasoning_state)
    followup_targets = derive_followup_targets(parsed, reasoning_state)
    followup_decision = classify_followup_decision(parsed, reasoning_state)
    why_followup = str(parsed.get("follow_up_reasoning") or reasoning_state.get("follow_up_reasoning") or "").strip()
    if not why_followup and followup_decision != "direct_answer":
        why_followup = "structured_followup_requested"
    reason_not_direct_answer = str(parsed.get("reason_not_direct_answer") or "").strip()
    if not reason_not_direct_answer and followup_decision != "direct_answer":
        reason_not_direct_answer = why_followup
    return {
        **parsed,
        "missing_high_impact_slots": missing_high_impact_slots,
        "followup_targets": followup_targets,
        "followup_decision_type": followup_decision,
        "why_followup": why_followup,
        "reason_not_direct_answer": reason_not_direct_answer,
        "followup_policy_source": "structured_manager_fields_only",
    }
