from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .retrieval_intent import RetrievalIntent

PipelineCaseFactory = Callable[..., Any]


def build_default_websearch_pipeline_cases(
    *,
    case_factory: PipelineCaseFactory,
) -> tuple[Any, ...]:
    intents = {
        "milksha": _intent(
            base_dish="pearl black tea latte",
            alias="Milksha pearl black tea latte",
            brand_hint="Milksha",
        ),
        "starbucks": _intent(
            base_dish="iced latte",
            alias="Starbucks iced latte large",
            brand_hint="Starbucks",
            size_hint="large",
        ),
        "milksha_half_sugar": _intent(
            base_dish="pearl black tea latte",
            alias="Milksha pearl black tea latte half sugar",
            brand_hint="Milksha",
            modifier_hints=("half sugar",),
        ),
    }
    return tuple(
        case_factory(
            case_id=case_id,
            intent=intents[intent_key],
            raw_hits=(
                _hit(
                    title=title,
                    url=url,
                    brand_detected=brand_detected,
                    **overrides,
                ),
            ),
        )
        for case_id, intent_key, title, url, brand_detected, overrides in _DEFAULT_CASE_DATA
    )


_DEFAULT_CASE_DATA: tuple[tuple[str, str, str, str, str, Mapping[str, Any]], ...] = (
    (
        "pipeline_milksha_exact", "milksha", "Milksha pearl black tea latte",
        "https://milksha.example/menu/pearl-black-tea-latte", "Milksha",
        {"identity_confidence": "high", "raw_ref": "raw/websearch/pipeline_milksha_exact.json#0"},
    ),
    (
        "pipeline_milksha_sibling", "milksha", "Milksha pearl fresh milk tea",
        "https://milksha.example/menu/pearl-fresh-milk-tea", "Milksha",
        {"identity_confidence": "medium", "raw_ref": "raw/websearch/pipeline_milksha_sibling.json#0"},
    ),
    (
        "pipeline_third_party_weak", "milksha", "Milksha pearl black tea latte calories",
        "https://third-party.example/milksha", "Milksha",
        {
            "officialness": "unknown",
            "source_quality_label": "low",
            "identity_confidence": "high",
            "raw_ref": "raw/websearch/pipeline_third_party_weak.json#0",
        },
    ),
    (
        "pipeline_starbucks_wrong_size", "starbucks", "Starbucks iced latte medium",
        "https://starbucks.example/menu/iced-latte-medium", "Starbucks",
        {"identity_confidence": "high", "raw_ref": "raw/websearch/pipeline_starbucks_wrong_size.json#0"},
    ),
    (
        "pipeline_official_pdf_exact", "milksha", "Milksha pearl black tea latte nutrition PDF",
        "https://milksha.example/nutrition/pearl-black-tea-latte.pdf", "Milksha",
        {
            "source_class": "official_nutrition_pdf",
            "identity_confidence": "high",
            "raw_ref": "raw/websearch/pipeline_official_pdf_exact.json#0",
        },
    ),
    (
        "pipeline_brand_menu_exact", "milksha", "Milksha pearl black tea latte",
        "https://milksha.example/menu/pearl-black-tea-latte", "Milksha",
        {
            "source_class": "brand_menu_page",
            "identity_confidence": "high",
            "raw_ref": "raw/websearch/pipeline_brand_menu_exact.json#0",
        },
    ),
    (
        "pipeline_robots_blocked", "milksha", "Milksha pearl black tea latte",
        "https://milksha.example/menu/robots-blocked", "Milksha",
        {
            "identity_confidence": "high",
            "robots_status": "blocked",
            "raw_ref": "raw/websearch/pipeline_robots_blocked.json#0",
        },
    ),
    (
        "pipeline_missing_serving_basis", "milksha", "Milksha pearl black tea latte",
        "https://milksha.example/menu/missing-serving", "Milksha",
        {
            "identity_confidence": "high",
            "serving_basis": "unknown",
            "raw_ref": "raw/websearch/pipeline_missing_serving_basis.json#0",
        },
    ),
    (
        "pipeline_missing_kcal", "milksha", "Milksha pearl black tea latte",
        "https://milksha.example/menu/missing-kcal", "Milksha",
        {
            "identity_confidence": "high",
            "nutrition_fields_present": [],
            "raw_ref": "raw/websearch/pipeline_missing_kcal.json#0",
        },
    ),
    (
        "pipeline_modifier_missing", "milksha_half_sugar", "Milksha pearl black tea latte",
        "https://milksha.example/menu/pearl-black-tea-latte", "Milksha",
        {"identity_confidence": "high", "raw_ref": "raw/websearch/pipeline_modifier_missing.json#0"},
    ),
    (
        "pipeline_wrong_brand_official", "milksha", "Other Tea pearl black tea latte",
        "https://other-tea.example/menu/pearl-black-tea-latte", "Other Tea",
        {"identity_confidence": "high", "raw_ref": "raw/websearch/pipeline_wrong_brand_official.json#0"},
    ),
    (
        "pipeline_social_media_untrusted", "milksha", "Milksha pearl black tea latte social post",
        "https://social.example/milksha/pearl-black-tea-latte", "Milksha",
        {
            "source_class": "social_media_page",
            "identity_confidence": "high",
            "raw_ref": "raw/websearch/pipeline_social_media_untrusted.json#0",
        },
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
    serving_basis: str = "per_cup",
    nutrition_fields_present: list[str] | None = None,
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
        "nutrition_fields_present": ["kcal"] if nutrition_fields_present is None else nutrition_fields_present,
        "license_status": "public_menu_page",
        "robots_status": robots_status,
        "customization_slots_present": ["size"],
        "identity_confidence": identity_confidence,
        "applicability_confidence": "medium",
        "applicability_notes": "deterministic fixture candidate",
        "raw_ref": raw_ref,
    }


__all__ = ["build_default_websearch_pipeline_cases"]
