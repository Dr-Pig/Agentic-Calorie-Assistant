from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import (
    _bounded_confidence,
    _list_of_dicts,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _menu_highlight_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    menu = fixture.get("menu_scan_context")
    parsed_items = (
        _list_of_dicts(menu.get("parsed_items")) if isinstance(menu, dict) else []
    )
    parse_confidence = _bounded_confidence(
        menu.get("parse_confidence") if isinstance(menu, dict) else None,
        default=0.0,
    )
    return _base_artifact(
        artifact_type="menu_highlight_shadow_eval",
        fixture=fixture,
        extra={
            "active_menu_scan_runtime_used": False,
            "ui_highlight_rendered": False,
            "candidate_source_only": True,
            "surface_policy": {
                "only_when_user_opens_or_provides_menu": True,
                "background_push_allowed": False,
                "current_surface_only": True,
            },
            "menu_highlights": [
                _highlight_item(item, candidates, parse_confidence)
                for item in parsed_items
            ],
            "review_policy": {
                "human_review_required": True,
                "highlight_promotion_allowed": False,
                "recommendation_served": False,
                "intake_commit_requested": False,
            },
        },
    )


def _highlight_item(
    item: dict[str, Any],
    candidates: list[LongTermContextCandidate],
    parse_confidence: float,
) -> dict[str, Any]:
    item_name = str(item.get("item_name") or "unknown_menu_item")
    positive = _matching_positive_candidates(item_name, candidates)
    negative = _matching_negative_candidates(item_name, candidates)
    matched = negative or positive
    return {
        "menu_item_name": item_name,
        "estimated_kcal_range": item.get("estimated_kcal_range") or [],
        "parse_confidence": _bounded_confidence(
            item.get("confidence"),
            default=parse_confidence,
        ),
        "highlight_status": _highlight_status(positive, negative),
        "source_candidate_ids": [candidate.candidate_id for candidate in matched],
        "memory_basis": [candidate.candidate_type for candidate in matched],
        "context_value_score": _context_value_score(matched, parse_confidence),
        "risk_if_wrong": _risk_if_wrong(bool(negative), bool(positive)),
        "annoyance_policy": "never_push_only_show_when_menu_is_active",
        "recommendation_served": False,
        "ui_highlight_rendered": False,
        "runtime_effect_allowed": False,
    }


def _matching_positive_candidates(
    item_name: str,
    candidates: list[LongTermContextCandidate],
) -> list[LongTermContextCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.candidate_type in {"food_preference", "golden_order"}
        and _candidate_matches_item(candidate, item_name)
    ]


def _matching_negative_candidates(
    item_name: str,
    candidates: list[LongTermContextCandidate],
) -> list[LongTermContextCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "negative_preference"
        and _candidate_matches_item(candidate, item_name)
    ]


def _candidate_matches_item(
    candidate: LongTermContextCandidate,
    item_name: str,
) -> bool:
    normalized = _normalize(item_name)
    if candidate.candidate_type == "golden_order":
        terms = [str(value) for value in candidate.payload.get("item_names") or []]
        return bool(terms) and all(_normalize(value) in normalized for value in terms)
    value = str(candidate.payload.get("value") or "")
    if value:
        return _normalize(value) in normalized
    return False


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


def _highlight_status(
    positive: list[LongTermContextCandidate],
    negative: list[LongTermContextCandidate],
) -> str:
    if negative:
        return "suppressed_by_negative_preference"
    if positive:
        return "eligible_positive_highlight"
    return "neutral_needs_more_context"


def _context_value_score(
    candidates: list[LongTermContextCandidate],
    parse_confidence: float,
) -> float:
    if not candidates:
        return round(parse_confidence * 0.25, 3)
    max_candidate_confidence = max(candidate.confidence for candidate in candidates)
    return round(min(1.0, parse_confidence * 0.35 + max_candidate_confidence * 0.65), 3)


def _risk_if_wrong(has_negative: bool, has_positive: bool) -> str:
    if has_negative:
        return "Could hide a menu item the user would accept if the dislike is stale."
    if has_positive:
        return "Could over-highlight a weak or stale food pattern."
    return "Could add visual noise without a clear memory-backed reason."


__all__ = ["_menu_highlight_shadow_artifact"]
