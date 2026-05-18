from __future__ import annotations

from typing import Any

_SEMANTIC_TARGET_KEYS = (
    "base_dish",
    "aliases",
    "brand_hint",
    "size_hint",
    "listed_items",
    "retrieval_goal",
)


def manager_semantic_decision_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        nested = value.get("manager_semantic_decision")
        return nested if isinstance(nested, dict) else value
    return {
        key: getattr(value, key)
        for key in _SEMANTIC_TARGET_KEYS
        if getattr(value, key, None) not in (None, "", [])
    }


def has_manager_owned_evidence_target(value: Any) -> bool:
    semantic_decision = manager_semantic_decision_payload(value)
    retrieval_goal = _text(semantic_decision.get("retrieval_goal"))
    listed_items = _text_list(semantic_decision.get("listed_items"))
    if retrieval_goal == "listed_item_lookup":
        return len(listed_items) >= 2
    if _text(semantic_decision.get("base_dish")):
        return True
    if _text_list(semantic_decision.get("aliases")):
        return True
    brand_hint = _text(semantic_decision.get("brand_hint"))
    size_hint = _text(semantic_decision.get("size_hint"))
    return bool(brand_hint and size_hint)


def manager_owned_listed_items(value: Any) -> list[str]:
    return _text_list(manager_semantic_decision_payload(value).get("listed_items"))


def manager_owned_target_failure_reason(value: Any) -> str | None:
    semantic_decision = manager_semantic_decision_payload(value)
    retrieval_goal = _text(semantic_decision.get("retrieval_goal"))
    listed_items = _text_list(semantic_decision.get("listed_items"))
    if retrieval_goal == "listed_item_lookup" and len(listed_items) < 2:
        return "listed_item_lookup_requires_multiple_manager_owned_items"
    if has_manager_owned_evidence_target(semantic_decision):
        return None
    return "estimate_nutrition_requires_manager_owned_evidence_target"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _text(item))]
