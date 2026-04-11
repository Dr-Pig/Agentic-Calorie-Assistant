from __future__ import annotations

from typing import Any


def source_class_for_item(item: dict[str, Any]) -> str:
    return str(item.get("source_class") or item.get("source_type") or "unknown")


def source_tier_for_item(item: dict[str, Any]) -> str:
    source_class = source_class_for_item(item)
    if source_class == "exact_item_db":
        return "tier_1_exact_verified"
    if source_class in {"recent_turns", "session_summary", "durable_memory"}:
        return "tier_2_context_verified"
    if source_class in {"base_nutrition_db", "meal_template_db"}:
        return "tier_3_anchor_prior"
    if source_class in {"doc_read_fallback", "web_search_official", "web_search_nonexact"}:
        return "tier_4_web_nonexact"
    return "tier_5_model_context"
