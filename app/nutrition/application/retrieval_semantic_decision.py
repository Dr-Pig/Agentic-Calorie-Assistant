from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .retrieval_intent import RetrievalGoal, RetrievalIntent

SemanticAuthoritySource = Literal["synthetic_manager_structured_fixture", "live_manager_structured_output"]

_ALLOWED_SEMANTIC_AUTHORITY_SOURCES = {"synthetic_manager_structured_fixture", "live_manager_structured_output"}
_ALLOWED_RETRIEVAL_GOALS = {
    "generic_anchor_lookup",
    "exact_brand_lookup",
    "listed_item_lookup",
    "composition_clarification",
    "query_only_answer",
}


@dataclass(frozen=True)
class B2ManagerSemanticDecision:
    base_dish: str | None
    aliases: list[str]
    brand_hint: str | None
    size_hint: str | None
    modifier_hints: list[str]
    listed_items: list[str]
    retrieval_goal: RetrievalGoal
    semantic_authority_source: SemanticAuthoritySource | str


def build_retrieval_intent_from_manager_decision(decision: B2ManagerSemanticDecision) -> RetrievalIntent:
    _validate_semantic_authority_source(decision.semantic_authority_source)
    _validate_retrieval_goal(decision.retrieval_goal)
    return RetrievalIntent(
        base_dish=_clean_optional_text(decision.base_dish),
        aliases=_clean_text_list(decision.aliases),
        brand_hint=_clean_optional_text(decision.brand_hint),
        size_hint=_clean_optional_text(decision.size_hint),
        modifier_hints=_clean_text_list(decision.modifier_hints),
        listed_items=_clean_text_list(decision.listed_items),
        retrieval_goal=decision.retrieval_goal,
    )


def _validate_semantic_authority_source(source: str) -> None:
    if source not in _ALLOWED_SEMANTIC_AUTHORITY_SOURCES:
        raise ValueError(f"semantic_authority_source must be manager-owned; got {source!r}")


def _validate_retrieval_goal(retrieval_goal: str) -> None:
    if retrieval_goal not in _ALLOWED_RETRIEVAL_GOALS:
        raise ValueError(f"retrieval_goal must use the B2 retrieval enum; got {retrieval_goal!r}")


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_text_list(values: list[str]) -> list[str]:
    return [cleaned for value in values if (cleaned := str(value).strip())]


__all__ = [
    "B2ManagerSemanticDecision",
    "SemanticAuthoritySource",
    "build_retrieval_intent_from_manager_decision",
]
