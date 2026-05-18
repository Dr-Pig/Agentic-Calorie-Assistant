from __future__ import annotations

from app.nutrition.application.retrieval_semantic_decision import B2ManagerSemanticDecision


def manager_owned_retrieval_query(
    manager_semantic_decision: B2ManagerSemanticDecision | None,
    *,
    raw_user_input: str | None = None,
) -> str | None:
    if manager_semantic_decision is None:
        return None
    base_dish = str(getattr(manager_semantic_decision, "base_dish", "") or "").strip()
    retrieval_goal = str(getattr(manager_semantic_decision, "retrieval_goal", "") or "").strip()
    if base_dish and retrieval_goal in {"generic_anchor_lookup", "listed_item_lookup", "exact_brand_lookup"}:
        brand_hint = str(getattr(manager_semantic_decision, "brand_hint", "") or "").strip()
        modifier_text = _manager_owned_modifier_text(manager_semantic_decision, raw_user_input=raw_user_input)
        if retrieval_goal == "exact_brand_lookup" and brand_hint and brand_hint not in base_dish:
            base_dish = f"{brand_hint} {base_dish}"
        if modifier_text and modifier_text not in base_dish:
            return f"{base_dish} {modifier_text}"
        return base_dish
    aliases = [
        str(item).strip()
        for item in getattr(manager_semantic_decision, "aliases", None) or []
        if str(item).strip()
    ]
    return aliases[0] if aliases else None


def manager_owned_listed_components(
    manager_semantic_decision: B2ManagerSemanticDecision | None,
) -> list[str] | None:
    if manager_semantic_decision is None:
        return None
    if str(getattr(manager_semantic_decision, "retrieval_goal", "") or "").strip() != "listed_item_lookup":
        return None
    return list(getattr(manager_semantic_decision, "listed_items", None) or []) or None


def manager_exact_lane_allowed(
    manager_semantic_decision: B2ManagerSemanticDecision | None,
) -> bool:
    if manager_semantic_decision is None:
        return False
    retrieval_goal = str(getattr(manager_semantic_decision, "retrieval_goal", "") or "").strip()
    listed_items = [
        str(item).strip()
        for item in getattr(manager_semantic_decision, "listed_items", None) or []
        if str(item).strip()
    ]
    return retrieval_goal == "exact_brand_lookup" and not listed_items


def _manager_owned_modifier_text(
    manager_semantic_decision: B2ManagerSemanticDecision,
    *,
    raw_user_input: str | None,
) -> str:
    del raw_user_input
    hints = [
        str(getattr(manager_semantic_decision, "size_hint", "") or "").strip(),
        *[str(item).strip() for item in getattr(manager_semantic_decision, "modifier_hints", None) or []],
    ]
    return " ".join(item for item in hints if item)


__all__ = [
    "manager_exact_lane_allowed",
    "manager_owned_listed_components",
    "manager_owned_retrieval_query",
]
