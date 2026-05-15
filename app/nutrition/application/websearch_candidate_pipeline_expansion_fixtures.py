from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .retrieval_intent import RetrievalIntent
from .websearch_candidate_pipeline_negative_fixtures import build_negative_websearch_pipeline_cases
from .websearch_candidate_pipeline_fixtures import build_default_websearch_pipeline_cases
PipelineCaseFactory = Callable[..., Any]

def build_expanded_websearch_pipeline_cases(*, case_factory: PipelineCaseFactory) -> tuple[Any, ...]:
    return (
        *build_default_websearch_pipeline_cases(case_factory=case_factory),
        _convenience_store_rice_ball_exact(case_factory),
        _chain_restaurant_menu_item_exact(case_factory),
        _multi_source_official_preferred(case_factory),
        _official_pdf_priority(case_factory),
        _large_size_preferred(case_factory),
        _size_unknown_requires_followup(case_factory),
        _modifier_match_preferred(case_factory),
        _same_brand_wrong_flavor_variant(case_factory),
        _all_blocked_candidates(case_factory),
        *build_negative_websearch_pipeline_cases(
            case_factory=case_factory,
            intent_factory=_intent,
            hit_factory=_hit,
        ),
    )


def _convenience_store_rice_ball_exact(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(
        base_dish="salmon rice ball",
        alias="7-Eleven salmon rice ball",
        brand_hint="7-Eleven",
    )
    return case_factory(
        case_id="pipeline_convenience_store_rice_ball_exact",
        intent=intent,
        raw_hits=(
            _hit(
                title="7-Eleven salmon rice ball",
                url="https://7-11.example/products/salmon-rice-ball",
                brand_detected="7-Eleven",
                source_class="official_brand_or_chain_page",
                identity_confidence="high",
                serving_basis="per_piece",
                customization_slots_present=(),
                raw_ref="raw/websearch/pipeline_convenience_store_rice_ball_exact.json#0",
            ),
        ),
    )


def _chain_restaurant_menu_item_exact(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(
        base_dish="gyudon",
        alias="Matsuya gyudon large",
        brand_hint="Matsuya",
        size_hint="large",
    )
    return case_factory(
        case_id="pipeline_chain_restaurant_menu_item_exact",
        intent=intent,
        raw_hits=(
            _hit(
                title="Matsuya gyudon large",
                url="https://matsuya.example/menu/gyudon-large",
                brand_detected="Matsuya",
                source_class="brand_menu_page",
                identity_confidence="high",
                serving_basis="per_bowl",
                raw_ref="raw/websearch/pipeline_chain_restaurant_menu_item_exact.json#0",
            ),
        ),
    )


def _multi_source_official_preferred(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(base_dish="pearl black tea latte", alias="Milksha pearl black tea latte", brand_hint="Milksha")
    return case_factory(
        case_id="pipeline_multi_source_official_preferred",
        intent=intent,
        raw_hits=(
            _hit(
                title="Milksha pearl black tea latte calories",
                url="https://third-party.example/milksha-calories",
                brand_detected="Milksha",
                officialness="unknown",
                source_quality_label="low",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_multi_source_official_preferred.json#0",
            ),
            _hit(
                title="Other Tea pearl black tea latte",
                url="https://other-tea.example/menu/pearl-black-tea-latte",
                brand_detected="Other Tea",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_multi_source_official_preferred.json#1",
            ),
            _hit(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/pearl-black-tea-latte",
                brand_detected="Milksha",
                source_class="brand_menu_page",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_multi_source_official_preferred.json#2",
            ),
        ),
    )


def _official_pdf_priority(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(base_dish="pearl black tea latte", alias="Milksha pearl black tea latte", brand_hint="Milksha")
    return case_factory(
        case_id="pipeline_official_pdf_priority",
        intent=intent,
        raw_hits=(
            _hit(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/pearl-black-tea-latte",
                brand_detected="Milksha",
                source_class="brand_menu_page",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_official_pdf_priority.json#0",
            ),
            _hit(
                title="Milksha pearl black tea latte nutrition PDF",
                url="https://milksha.example/nutrition/pearl-black-tea-latte.pdf",
                brand_detected="Milksha",
                source_class="official_nutrition_pdf",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_official_pdf_priority.json#1",
            ),
        ),
    )


def _large_size_preferred(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(base_dish="iced latte", alias="Starbucks iced latte large", brand_hint="Starbucks", size_hint="large")
    return case_factory(
        case_id="pipeline_large_size_preferred",
        intent=intent,
        raw_hits=(
            _hit(
                title="Starbucks iced latte medium",
                url="https://starbucks.example/menu/iced-latte-medium",
                brand_detected="Starbucks",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_large_size_preferred.json#0",
            ),
            _hit(
                title="Starbucks iced latte large",
                url="https://starbucks.example/menu/iced-latte-large",
                brand_detected="Starbucks",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_large_size_preferred.json#1",
            ),
        ),
    )


def _size_unknown_requires_followup(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(
        base_dish="iced latte",
        alias="Starbucks iced latte large",
        brand_hint="Starbucks",
        size_hint="large",
    )
    return case_factory(
        case_id="pipeline_size_unknown_requires_followup",
        intent=intent,
        raw_hits=(
            _hit(
                title="Starbucks iced latte",
                url="https://starbucks.example/menu/iced-latte",
                brand_detected="Starbucks",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_size_unknown_requires_followup.json#0",
            ),
        ),
    )


def _modifier_match_preferred(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(base_dish="pearl black tea latte", alias="Milksha pearl black tea latte half sugar", brand_hint="Milksha", modifier_hints=("half sugar",))
    return case_factory(
        case_id="pipeline_modifier_match_preferred",
        intent=intent,
        raw_hits=(
            _hit(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/pearl-black-tea-latte",
                brand_detected="Milksha",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_modifier_match_preferred.json#0",
            ),
            _hit(
                title="Milksha pearl black tea latte half sugar",
                url="https://milksha.example/menu/pearl-black-tea-latte-half-sugar",
                brand_detected="Milksha",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_modifier_match_preferred.json#1",
            ),
        ),
    )


def _same_brand_wrong_flavor_variant(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(
        base_dish="pearl black tea latte",
        alias="Milksha pearl black tea latte",
        brand_hint="Milksha",
    )
    return case_factory(
        case_id="pipeline_same_brand_wrong_flavor_variant",
        intent=intent,
        raw_hits=(
            _hit(
                title="Milksha pearl fresh milk tea",
                url="https://milksha.example/menu/pearl-fresh-milk-tea",
                brand_detected="Milksha",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_same_brand_wrong_flavor_variant.json#0",
            ),
        ),
    )


def _all_blocked_candidates(case_factory: PipelineCaseFactory) -> Any:
    intent = _intent(base_dish="pearl black tea latte", alias="Milksha pearl black tea latte", brand_hint="Milksha")
    return case_factory(
        case_id="pipeline_all_candidates_blocked",
        intent=intent,
        raw_hits=(
            _hit(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/unknown-license",
                brand_detected="Milksha",
                identity_confidence="high",
                license_status="unknown",
                raw_ref="raw/websearch/pipeline_all_candidates_blocked.json#0",
            ),
            _hit(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/robots-blocked",
                brand_detected="Milksha",
                identity_confidence="high",
                robots_status="blocked",
                raw_ref="raw/websearch/pipeline_all_candidates_blocked.json#1",
            ),
            _hit(
                title="Other Tea pearl black tea latte",
                url="https://other-tea.example/menu/pearl-black-tea-latte",
                brand_detected="Other Tea",
                identity_confidence="high",
                raw_ref="raw/websearch/pipeline_all_candidates_blocked.json#2",
            ),
        ),
    )


def _intent(
    *,
    base_dish: str,
    alias: str,
    brand_hint: str,
    size_hint: str | None = None,
    modifier_hints: tuple[str, ...] = (),
) -> RetrievalIntent:
    return RetrievalIntent(
        base_dish=base_dish,
        aliases=[alias],
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=list(modifier_hints),
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _hit(
    *,
    title: str,
    url: str,
    brand_detected: str,
    source_class: str | None = None,
    officialness: str = "official",
    source_quality_label: str = "high",
    identity_confidence: str = "medium",
    robots_status: str = "allowed",
    license_status: str = "public_menu_page",
    serving_basis: str = "per_cup",
    customization_slots_present: tuple[str, ...] = ("size",),
    raw_ref: str,
) -> dict[str, Any]:
    return {
        "url": url,
        "domain": "example.test",
        "title": title,
        "snippet": "deterministic search candidate",
        "score": 0.93,
        "officialness": officialness,
        "source_class": source_class,
        "source_quality_label": source_quality_label,
        "brand_detected": brand_detected,
        "channel_detected": "handmade_foodservice",
        "serving_basis": serving_basis,
        "nutrition_fields_present": ["kcal"],
        "license_status": license_status,
        "robots_status": robots_status,
        "customization_slots_present": list(customization_slots_present),
        "identity_confidence": identity_confidence,
        "applicability_confidence": "medium",
        "applicability_notes": "deterministic fixture candidate",
        "raw_ref": raw_ref,
    }
