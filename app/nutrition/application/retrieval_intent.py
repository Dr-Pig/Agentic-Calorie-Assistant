from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re

RetrievalGoal = Literal[
    "generic_anchor_lookup",
    "exact_brand_lookup",
    "listed_item_lookup",
    "composition_clarification",
    "query_only_answer",
]

RAW_TEXT_RETRIEVAL_INTENT_POLICY = {
    "semantic_authority_source": "deterministic_raw_text_hint_only",
    "user_intent_owner": "manager_llm",
    "workflow_owner": "manager_llm",
    "mutation_owner": "runtime_guard",
    "allowed_uses": [
        "retrieval_candidate_recall",
        "source_selection_hint",
        "diagnostic_fixture_seed",
    ],
    "forbidden_uses": [
        "user_intent_classification",
        "workflow_effect_decision",
        "final_action_selection",
        "mutation_authority",
    ],
}

_KNOWN_BRANDS = (
    "\u677e\u5c4b",
    "\u661f\u5df4\u514b",
    "\u722d\u9bae",
    "\u7d71\u4e00",
)
_SIZE_HINTS = (
    "\u7279\u76db",
    "\u5927\u676f",
    "\u4e2d\u676f",
    "\u5c0f\u676f",
    "400ml",
    "\u5169\u8cab",
)
_QUERY_MARKERS = (
    "\u591a\u5c11\u71b1\u91cf",
    "\u5e7e\u5361",
    "\u5361\u8def\u91cc",
    "\u71b1\u91cf",
    "\uff1f",
    "?",
)
_LEADING_PREFIXES = (
    "\u6211\u5403\u4e86",
    "\u6211\u559d\u4e86",
    "\u6211\u8cb7\u4e86",
    "\u6211\u665a\u9910\u5403",
    "\u665a\u9910\u5403",
    "\u5bb5\u591c\u5403",
    "\u4eca\u5929\u5403\u4e86",
    "\u4eca\u5929\u559d\u4e86",
    "\u5403\u4e86",
    "\u559d\u4e86",
)
_COMPOSITION_UNKNOWN_BASKETS = (
    "\u6ef7\u5473",
    "\u9ebb\u8fa3\u71d9",
    "\u81ea\u52a9\u9910",
    "\u9e79\u6c34\u96de",
    "\u95dc\u6771\u716e",
)
_SALT_CRISPY_CHICKEN = "\u9e7d\u9165\u96de"
_HOMEMADE_BARE_TERMS = (
    "\u5bb6\u5e38\u83dc",
    "\u5abd\u5abd\u716e\u7684",
)
_SIMPLE_QUANTITY_PREFIX = re.compile(
    r"^(?P<prefix>(?:[12\u4e00\u5169\u4e8c])(?:\u9846|\u676f|\u500b|\u4efd|\u7897|\u689d|\u7247|\u584a|\u4e32|\u7403|\u5305|\u76d2|\u74f6))"
)


@dataclass(frozen=True)
class RetrievalIntent:
    base_dish: str | None
    aliases: list[str]
    brand_hint: str | None
    size_hint: str | None
    modifier_hints: list[str]
    listed_items: list[str]
    retrieval_goal: RetrievalGoal


def build_raw_text_retrieval_hint(user_input: str) -> RetrievalIntent:
    """Build a raw-text retrieval hint without semantic authority.

    This helper is allowed to support candidate recall and diagnostic fixtures.
    It must not own user intent, workflow effect, final action, or mutation.
    """

    normalized = str(user_input or "").strip()
    listed_items = _extract_listed_items(normalized)
    brand_hint = _extract_brand_hint(normalized)
    size_hint = _extract_size_hint(normalized)
    base_dish = _extract_base_dish(
        normalized,
        brand_hint=brand_hint,
        size_hint=size_hint,
        listed_items=listed_items,
    )
    retrieval_goal = _select_retrieval_goal(
        normalized,
        brand_hint=brand_hint,
        listed_items=listed_items,
        base_dish=base_dish,
    )
    aliases = _aliases_for_intent(normalized, base_dish)
    return RetrievalIntent(
        base_dish=base_dish,
        aliases=aliases,
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=[],
        listed_items=listed_items,
        retrieval_goal=retrieval_goal,
    )


def build_diagnostic_retrieval_intent(user_input: str) -> RetrievalIntent:
    """Explicit diagnostic-only alias for raw-text retrieval hint generation."""

    return build_raw_text_retrieval_hint(user_input)


def build_retrieval_intent(user_input: str) -> RetrievalIntent:
    """Backward-compatible diagnostic alias.

    This entrypoint must stay diagnostic-only. Runtime evidence execution must
    use a manager-owned retrieval request instead.
    """

    return build_diagnostic_retrieval_intent(user_input)


def _extract_listed_items(user_input: str) -> list[str]:
    match = re.search(r"(?P<items>.+?)\u7684\u6ef7\u5473", user_input)
    if match:
        items_blob = match.group("items").strip()
    else:
        salt_match = re.search(r"\u9e7d\u9165\u96de[\uff0c,]\u6709(?P<items>.+)$", user_input)
        if not salt_match:
            return []
        items_blob = salt_match.group("items").strip()
    items_blob = _strip_leading_prefix(items_blob)
    return [item.strip() for item in re.split(r"[\u3001,/\uff0c]", items_blob) if item.strip()]


def _extract_brand_hint(user_input: str) -> str | None:
    for brand in _KNOWN_BRANDS:
        if brand in user_input:
            return brand
    return None


def _extract_size_hint(user_input: str) -> str | None:
    for hint in _SIZE_HINTS:
        if hint in user_input:
            return hint
    return None


def _extract_base_dish(
    user_input: str,
    *,
    brand_hint: str | None,
    size_hint: str | None,
    listed_items: list[str],
) -> str | None:
    if listed_items:
        if _SALT_CRISPY_CHICKEN in user_input:
            return _SALT_CRISPY_CHICKEN
        return "\u6ef7\u5473"

    dish = user_input
    dish = _strip_leading_prefix(dish)
    dish = _strip_simple_quantity_prefix(dish)
    if dish.endswith("\u6ef7\u5473"):
        return "\u6ef7\u5473"
    if brand_hint:
        dish = dish.replace(brand_hint, "", 1)
    if size_hint:
        dish = dish.replace(size_hint, "", 1)
    for marker in _QUERY_MARKERS:
        dish = dish.replace(marker, "")
    cleaned = dish.strip(" ()\u3000\u300c\u300d\u300e\u300f\"'")
    if cleaned.startswith(_SALT_CRISPY_CHICKEN):
        return _SALT_CRISPY_CHICKEN
    return cleaned or None


def _select_retrieval_goal(
    user_input: str,
    *,
    brand_hint: str | None,
    listed_items: list[str],
    base_dish: str | None,
) -> RetrievalGoal:
    if listed_items:
        return "listed_item_lookup"
    if _looks_like_query_only(user_input):
        return "query_only_answer"
    if base_dish in _COMPOSITION_UNKNOWN_BASKETS:
        return "composition_clarification"
    if base_dish == _SALT_CRISPY_CHICKEN and not _has_salt_crispy_chicken_portion_cue(user_input):
        return "composition_clarification"
    if base_dish in _HOMEMADE_BARE_TERMS:
        return "composition_clarification"
    if brand_hint:
        return "exact_brand_lookup"
    return "generic_anchor_lookup"


def _aliases_for_intent(user_input: str, base_dish: str | None) -> list[str]:
    aliases: list[str] = []
    for candidate in (base_dish, user_input):
        if not candidate or candidate == user_input or candidate in aliases:
            continue
        aliases.append(candidate)
    return aliases


def _strip_leading_prefix(text: str) -> str:
    for prefix in _LEADING_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text.strip()


def _looks_like_query_only(user_input: str) -> bool:
    return any(marker in user_input for marker in _QUERY_MARKERS)


def _strip_simple_quantity_prefix(text: str) -> str:
    stripped = str(text or "").strip()
    match = _SIMPLE_QUANTITY_PREFIX.match(stripped)
    if match is None:
        return stripped
    return stripped[match.end() :].strip()


def _has_salt_crispy_chicken_portion_cue(user_input: str) -> bool:
    return any(cue in user_input for cue in ("\u4e00\u4efd", "\u4e00\u5305", "\u5c0f\u4efd", "\u5927\u4efd", "50\u5143", "\u4e94\u5341\u5143"))


__all__ = [
    "RAW_TEXT_RETRIEVAL_INTENT_POLICY",
    "RetrievalIntent",
    "RetrievalGoal",
    "build_diagnostic_retrieval_intent",
    "build_raw_text_retrieval_hint",
    "build_retrieval_intent",
]
