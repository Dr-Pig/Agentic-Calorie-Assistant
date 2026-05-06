from __future__ import annotations

from collections.abc import Callable
from typing import Any
from .retrieval_intent import RetrievalIntent
from .websearch_candidate_pipeline_fixtures import build_default_websearch_pipeline_cases

PipelineCaseFactory = Callable[..., Any]


def build_expanded_websearch_pipeline_cases(*, case_factory: PipelineCaseFactory) -> tuple[Any, ...]:
    return (
        *build_default_websearch_pipeline_cases(case_factory=case_factory),
        _multi_source_official_preferred(case_factory),
        _official_pdf_priority(case_factory),
        _large_size_preferred(case_factory),
        _modifier_match_preferred(case_factory),
        _all_blocked_candidates(case_factory),
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
        "serving_basis": "per_cup",
        "nutrition_fields_present": ["kcal"],
        "license_status": license_status,
        "robots_status": robots_status,
        "customization_slots_present": ["size"],
        "identity_confidence": identity_confidence,
        "applicability_confidence": "medium",
        "applicability_notes": "deterministic fixture candidate",
        "raw_ref": raw_ref,
    }
__all__ = ["build_expanded_websearch_pipeline_cases"]
