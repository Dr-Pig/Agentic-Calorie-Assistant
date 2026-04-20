from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .recommendation_context import RecommendationContextPacket

RecommendationMealStyle = Literal["any", "light", "filling", "hot", "cold"]
RecommendationVenuePosture = Literal["any", "convenience_store", "restaurant"]
RecommendationSpecPosture = Literal["semantic_blueprint", "budget_constrained", "cold_start_fallback"]


@dataclass(frozen=True)
class RecommendationCandidateSpec:
    desired_meal_style: RecommendationMealStyle = "any"
    desired_cuisine_families: tuple[str, ...] = ()
    desired_item_kinds: tuple[str, ...] = ()
    desired_store_names: tuple[str, ...] = ()
    excluded_item_kinds: tuple[str, ...] = ()
    excluded_item_patterns: tuple[str, ...] = ()
    retrieval_terms: tuple[str, ...] = ()
    target_kcal_min: int = 0
    target_kcal_max: int = 0
    venue_posture: RecommendationVenuePosture = "any"
    swaps_allowed: bool = False
    handoff_ready: bool = False
    priority_signals: tuple[str, ...] = field(default_factory=tuple)
    candidate_spec_posture: RecommendationSpecPosture = "semantic_blueprint"
    handoff_ready: bool = True


def _normalized_text(raw_user_input: str) -> str:
    return " ".join(raw_user_input.strip().lower().replace("/", " ").split())


def _contains_any(normalized: str, tokens: tuple[str, ...]) -> bool:
    return any(token in normalized for token in tokens)


def _desired_meal_style(raw_user_input: str) -> RecommendationMealStyle:
    normalized = _normalized_text(raw_user_input)
    if _contains_any(normalized, ("light", "lighter", "light meal", "low burden")):
        return "light"
    if _contains_any(normalized, ("hot", "warm")):
        return "hot"
    if _contains_any(normalized, ("cold", "chilled")):
        return "cold"
    if _contains_any(normalized, ("filling", "hearty", "full meal")):
        return "filling"
    return "any"


def _venue_posture(raw_user_input: str) -> RecommendationVenuePosture:
    normalized = _normalized_text(raw_user_input)
    if _contains_any(normalized, ("convenience", "7-11", "familymart")):
        return "convenience_store"
    if _contains_any(normalized, ("restaurant", "dine in", "outside")):
        return "restaurant"
    return "any"


def _desired_item_kinds(desired_meal_style: RecommendationMealStyle) -> tuple[str, ...]:
    if desired_meal_style == "light":
        return ("salad", "light_meal", "snack")
    if desired_meal_style == "filling":
        return ("meal", "bowl", "main_meal")
    return ()


def _desired_store_names(context_packet: RecommendationContextPacket) -> tuple[str, ...]:
    return tuple(value.lower() for value in context_packet.soft_preferences.preferred_store_names if value)[:3]


def _desired_cuisine_families(context_packet: RecommendationContextPacket) -> tuple[str, ...]:
    return tuple(value.lower() for value in context_packet.soft_preferences.preferred_cuisine_families if value)[:3]


def _excluded_item_kinds(
    *,
    context_packet: RecommendationContextPacket,
    desired_meal_style: RecommendationMealStyle,
) -> tuple[str, ...]:
    excluded: list[str] = []
    if desired_meal_style == "light":
        excluded.extend(["fried", "dessert"])
    if context_packet.hard_constraints.rescue_active:
        excluded.append("heavy_meal")
    return tuple(dict.fromkeys(excluded))


def _excluded_item_patterns(
    *,
    context_packet: RecommendationContextPacket,
    desired_meal_style: RecommendationMealStyle,
) -> tuple[str, ...]:
    excluded: list[str] = []
    if desired_meal_style == "light":
        excluded.extend(["fried", "sugary", "heavy_sauce"])
    elif context_packet.hard_constraints.rescue_active:
        excluded.append("heavy_sauce")
    return tuple(dict.fromkeys(excluded))


def _target_kcal_band(context_packet: RecommendationContextPacket) -> tuple[int, int]:
    remaining = max(0, int(context_packet.hard_constraints.remaining_budget_kcal or 0))
    if remaining <= 0:
        return 0, 0
    if context_packet.budget_posture == "tight_budget":
        return max(120, int(remaining * 0.35)), remaining
    return max(180, int(remaining * 0.45)), remaining


def _retrieval_terms(
    *,
    context_packet: RecommendationContextPacket,
    desired_meal_style: RecommendationMealStyle,
    venue_posture: RecommendationVenuePosture,
) -> tuple[str, ...]:
    terms: list[str] = []
    if venue_posture == "convenience_store":
        terms.append("convenience")
    if context_packet.hard_constraints.location_required:
        terms.append("nearby")
    if desired_meal_style != "any":
        terms.append(desired_meal_style)
    return tuple(terms)


def _priority_signals(
    *,
    context_packet: RecommendationContextPacket,
    desired_meal_style: RecommendationMealStyle,
) -> tuple[str, ...]:
    signals: list[str] = ["within_remaining_budget", "avoid_repeat_from_today"]
    protein_posture = str(context_packet.soft_preferences.protein_posture_preference or "").strip().lower()
    if protein_posture in {"high_protein", "high_protein_bias"}:
        signals.append("high_protein")
    if desired_meal_style != "any":
        signals.append(f"style:{desired_meal_style}")
    if context_packet.hard_constraints.rescue_active:
        signals.append("rescue_safe")
    return tuple(signals)


def build_recommendation_candidate_spec(
    *,
    context_packet: RecommendationContextPacket,
) -> RecommendationCandidateSpec:
    desired_meal_style = _desired_meal_style(context_packet.raw_user_input)
    venue_posture = _venue_posture(context_packet.raw_user_input)
    posture: RecommendationSpecPosture = "semantic_blueprint"
    if context_packet.recommendation_mode == "cold_start":
        posture = "cold_start_fallback"
    elif context_packet.budget_posture in {"tight_budget", "over_budget"}:
        posture = "budget_constrained"
    target_kcal_min, target_kcal_max = _target_kcal_band(context_packet)

    return RecommendationCandidateSpec(
        desired_meal_style=desired_meal_style,
        desired_cuisine_families=_desired_cuisine_families(context_packet),
        desired_item_kinds=_desired_item_kinds(desired_meal_style),
        desired_store_names=_desired_store_names(context_packet),
        excluded_item_kinds=_excluded_item_kinds(
            context_packet=context_packet,
            desired_meal_style=desired_meal_style,
        ),
        excluded_item_patterns=_excluded_item_patterns(
            context_packet=context_packet,
            desired_meal_style=desired_meal_style,
        ),
        retrieval_terms=_retrieval_terms(
            context_packet=context_packet,
            desired_meal_style=desired_meal_style,
            venue_posture=venue_posture,
        ),
        target_kcal_min=target_kcal_min,
        target_kcal_max=target_kcal_max,
        venue_posture=venue_posture,
        swaps_allowed="swap" in _normalized_text(context_packet.raw_user_input),
        handoff_ready=True,
        priority_signals=_priority_signals(
            context_packet=context_packet,
            desired_meal_style=desired_meal_style,
        ),
        candidate_spec_posture=posture,
    )
