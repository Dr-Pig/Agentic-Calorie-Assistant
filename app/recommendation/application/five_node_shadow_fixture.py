from __future__ import annotations

from typing import Any

from app.recommendation.application.three_node_shadow_policy import (
    build_fixture_recommendation_three_node_input,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.five_node_shadow_fixture"
)


def build_fixture_recommendation_five_node_input() -> dict[str, Any]:
    payload = build_fixture_recommendation_three_node_input()
    payload.update(
        {
            "recommendation_context_fixture": {
                "decision_mode": "llm_fixture",
                "context_summary": "fixture LLM framed budget, dislikes, rescue state",
            },
            "candidate_spec_fixture": {
                "decision_mode": "llm_fixture",
                "intent": "suggest_budget_fitting_order",
                "constraints": ["budget", "negative_preference", "open_rescue"],
            },
            "ranking_synthesis_fixture": {
                "decision_mode": "llm_fixture",
                "selected_candidate_id": "golden-1",
                "ranked_candidate_ids": ["golden-1"],
                "rationale": "budget-fitting golden order survives deterministic guard",
            },
            "response_offer_fixture": {
                "decision_mode": "llm_fixture",
                "candidate_id": "golden-1",
                "recommendation_served": False,
                "is_canonical_truth": False,
                "intake_commit_requested": False,
            },
        }
    )
    return payload


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_fixture_recommendation_five_node_input"]
