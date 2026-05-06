from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .retrieval_intent import RetrievalIntent

PipelineCaseFactory = Callable[..., Any]


def build_negative_websearch_pipeline_cases(
    *,
    case_factory: PipelineCaseFactory,
    intent_factory: Callable[..., RetrievalIntent],
    hit_factory: Callable[..., dict[str, Any]],
) -> tuple[Any, ...]:
    return (
        _wrong_country_menu(case_factory, intent_factory=intent_factory, hit_factory=hit_factory),
        _serving_size_not_listed(
            case_factory,
            intent_factory=intent_factory,
            hit_factory=hit_factory,
        ),
    )


def _wrong_country_menu(
    case_factory: PipelineCaseFactory,
    *,
    intent_factory: Callable[..., RetrievalIntent],
    hit_factory: Callable[..., dict[str, Any]],
) -> Any:
    intent = intent_factory(
        base_dish="gyudon",
        alias="Matsuya gyudon large",
        brand_hint="Matsuya",
        size_hint="large",
    )
    return case_factory(
        case_id="pipeline_wrong_country_menu",
        intent=intent,
        raw_hits=(
            hit_factory(
                title="Matsuya Hong Kong gyudon large",
                url="https://matsuya.example/hk/menu/gyudon-large",
                brand_detected="Matsuya",
                source_class="brand_menu_page",
                identity_confidence="high",
                serving_basis="per_bowl",
                raw_ref="raw/websearch/pipeline_wrong_country_menu.json#0",
            ),
        ),
    )


def _serving_size_not_listed(
    case_factory: PipelineCaseFactory,
    *,
    intent_factory: Callable[..., RetrievalIntent],
    hit_factory: Callable[..., dict[str, Any]],
) -> Any:
    intent = intent_factory(
        base_dish="pearl black tea latte",
        alias="Milksha pearl black tea latte",
        brand_hint="Milksha",
    )
    return case_factory(
        case_id="pipeline_serving_size_not_listed",
        intent=intent,
        raw_hits=(
            hit_factory(
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/pearl-black-tea-latte-no-serving",
                brand_detected="Milksha",
                source_class="brand_menu_page",
                identity_confidence="high",
                serving_basis="unknown",
                raw_ref="raw/websearch/pipeline_serving_size_not_listed.json#0",
            ),
        ),
    )


__all__ = ["build_negative_websearch_pipeline_cases"]
