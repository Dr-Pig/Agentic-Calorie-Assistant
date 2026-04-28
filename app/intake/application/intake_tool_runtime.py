from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ...shared.contracts.intake import ComponentEstimate, EstimatePayload
from ...shared.domain import ConversationState


@dataclass(frozen=True)
class PersistMealLogResult:
    action: str
    status: str | None
    persisted_log_id: int | None
    linked_meal_log_id: int | None
    canonical_commit: dict[str, Any] | None


def conversation_pending_followup(conversation_state: ConversationState | Any) -> dict[str, Any]:
    pending = getattr(conversation_state, "pending_followup_state", None)
    if pending is None:
        return {
            "is_open": False,
            "source_meal_id": None,
            "pending_question": None,
            "missing_high_impact_slots": [],
        }
    if hasattr(pending, "model_dump"):
        return pending.model_dump(mode="json")
    return dict(pending)


def trace_slots(trace_contract: dict[str, Any], key: str) -> list[str]:
    return [str(item) for item in trace_contract.get(key, []) if str(item).strip()]


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


_GENERIC_MILK_TEA_TOKENS = ("??憟嗉", "憟嗉", "milk tea", "bubble tea")
_BRAND_PACKAGE_TOKENS = ("7-11", "city cafe", "?典振", "familymart", "coco", "50撋?", "鈭?撋?", "?臭???", "暻餃")
_SIZE_TOKENS = ("憭扳", "銝剜", "撠", "l??", "m??", "s??", "憭?", "銝?", "撠?")
_SWEETNESS_TOKENS = ("?函?", "??", "敺桃?", "撠?", "?∠?", "甇?虜蝟?")
_COUNT_ANCHOR_PATTERN = re.compile(r"\d+\s*(憿?蝎隞罵pcs?|pieces?)", re.IGNORECASE)
_MULTI_ITEM_SPLIT_TOKENS = ("\u548c", "\u3001", ",", "\uff0c", "\u9084\u6709", "+")


def looks_like_generic_milk_tea(raw_user_input: str, *, family_rule: str | None = None) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _GENERIC_MILK_TEA_TOKENS) or family_rule == "generic_milk_tea"


def has_brand_or_package_cue(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _BRAND_PACKAGE_TOKENS)


def has_structuring_drink_details(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _SIZE_TOKENS) and any(token in normalized for token in _SWEETNESS_TOKENS)


def has_count_anchor(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return bool(_COUNT_ANCHOR_PATTERN.search(normalized))


def looks_like_multi_item_input(raw_user_input: str) -> bool:
    normalized = str(raw_user_input or "").strip().lower()
    if any(token in normalized for token in _MULTI_ITEM_SPLIT_TOKENS):
        return True
    quantity_markers = ["銝蝣?", "銝??", "銝憿?", "銝??", "銝隞?"]
    return sum(1 for token in quantity_markers if token in normalized) >= 2


def normalize_live_payload(payload: EstimatePayload, *, raw_user_input: str, family_rule: str | None = None, high_variance: bool = False) -> None:
    if (
        payload.component_breakdown
        and (
            not payload.component_estimates
            or all(int(component.estimated_kcal or 0) <= 0 for component in payload.component_estimates)
        )
    ):
        payload.component_estimates = [
            ComponentEstimate(
                name=str(item.get("name") or "item"),
                quantity_hint=str(item.get("quantity_hint") or item.get("portion_basis") or "").strip() or None,
                estimated_kcal=int(item.get("estimated_kcal") or 0),
                protein_g=int(item.get("protein_g") or 0),
                carb_g=int(item.get("carb_g") or 0),
                fat_g=int(item.get("fat_g") or 0),
            )
            for item in payload.component_breakdown
            if int(item.get("estimated_kcal") or 0) > 0
        ]

    trace_contract = payload.trace_contract
    has_followup = bool(payload.followup_question) or bool(trace_slots(trace_contract, "unresolved_info"))
    has_blocking = bool(trace_slots(trace_contract, "blocking_slots"))
    has_missing = bool(trace_slots(trace_contract, "missing_slots"))
    clarify_first = str(trace_contract.get("response_mode_hint") or "") == "clarify_first"

    if payload.estimated_kcal > 0 and payload.route_target == "clarify_user_private" and not has_followup and not has_blocking and not has_missing and not clarify_first:
        payload.route_target = "best_effort_answer"

    if payload.estimated_kcal > 0 and payload.action_taken == "answer_with_uncertainty" and not has_followup and not has_blocking and not has_missing:
        payload.follow_up_needed = False

    if high_variance and payload.estimated_kcal > 0 and not has_brand_or_package_cue(raw_user_input) and not has_structuring_drink_details(raw_user_input) and not has_count_anchor(raw_user_input):
        payload.route_target = "clarify_user_private"
        payload.action_taken = "answer_with_uncertainty"
        payload.follow_up_needed = True
        if not str(payload.followup_question or "").strip():
            if family_rule == "generic_milk_tea" or looks_like_generic_milk_tea(raw_user_input, family_rule=family_rule):
                payload.followup_question = "隢??臬嗾????暻潭??"
            elif family_rule == "dumpling_count_required":
                payload.followup_question = "隢?憭扳???撟暸?嚗?"
            else:
                payload.followup_question = "???閬摰????隞賡?嚗??賣???閮???"
        payload.trace_contract = {
            **dict(payload.trace_contract or {}),
            "bundle2_guard_family": family_rule or "high_variance_followup_required",
            "why_not_exact": ["high_variance_family_requires_followup", "missing_identity_or_customization"],
        }
