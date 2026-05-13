from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_premeal_planning import (
    premeal_context,
)
from app.advanced_shadow_lab.product_lab_swap_suggestion import (
    swap_suggestion_context,
)
from app.recommendation.application.offer_synthesis_fixture_provider import (
    FixtureRecommendationOfferSynthesisProvider,
)
from app.recommendation.application.planning_fixture_provider import (
    FixtureRecommendationPlanningProvider,
)


class FixtureProductLabRecommendationProvider:
    provider_name = "fixture_product_lab_llm"
    planning_model_profile = "fast_router_model"
    offer_model_profile = "strict_reasoner_or_response_writer_model"

    def profile(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "planning_model_profile": self.planning_model_profile,
            "offer_model_profile": self.offer_model_profile,
            "model_dependency_inverted": True,
        }

    def plan(
        self,
        *,
        turn: Mapping[str, Any],
        fixture_inputs: Mapping[str, Any],
        memory_context_pack: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = _mapping(fixture_inputs.get("recommendation_payload"))
        premeal = premeal_context(turn=turn, payload=payload)
        swap = swap_suggestion_context(turn=turn, payload=payload)
        return FixtureRecommendationPlanningProvider(
            model_profile=self.planning_model_profile
        ).plan(
            turn=turn,
            fixture_inputs=fixture_inputs,
            memory_context_pack=memory_context_pack,
            pre_meal_planning=premeal,
            swap_suggestion=swap,
        )

    def synthesize_offer(
        self,
        *,
        retrieval_guard_scoring: Mapping[str, Any],
    ) -> dict[str, Any]:
        return FixtureRecommendationOfferSynthesisProvider(
            model_profile=self.offer_model_profile
        ).synthesize(retrieval_guard_scoring=retrieval_guard_scoring)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["FixtureProductLabRecommendationProvider"]
