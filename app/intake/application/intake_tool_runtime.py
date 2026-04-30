from __future__ import annotations

import json
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


_MULTI_ITEM_SPLIT_TOKENS = ("\u548c", "\u3001", ",", "\uff0c", "\u9084\u6709", "+")


def looks_like_multi_item_input(raw_user_input: str) -> bool:
    normalized = str(raw_user_input or "").strip().lower()
    return any(token in normalized for token in _MULTI_ITEM_SPLIT_TOKENS)


def normalize_live_payload(
    payload: EstimatePayload,
    *,
    raw_user_input: str,
    family_rule: str | None = None,
    high_variance: bool = False,
) -> None:
    del raw_user_input, family_rule, high_variance
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
