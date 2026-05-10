from __future__ import annotations

from typing import Any

from app.recommendation.application.three_node_live_preflight import FALSE_ACTIVATION_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_diagnostic_fake_provider"
)


class FakeRecommendationThreeNodeDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-recommendation-three-node", "configured": True}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        node = str(kwargs["user_payload"]["physical_node"])
        if node == "recommendation_planning":
            return fake_planning_output(), fake_trace(node)
        return fake_offer_output(), fake_trace(node)


def fake_planning_output() -> dict[str, Any]:
    return {
        "recommendation_context_result": {"recommendation_goal": "fixture_budget_fit"},
        "candidate_spec": {"desired_meal_style": "light"},
        "non_serve_flags": dict(FALSE_ACTIVATION_FLAGS),
    }


def fake_offer_output() -> dict[str, Any]:
    return {
        "ranking_result": {"selected_candidate_id": "golden-1", "backup_candidate_ids": []},
        "recommendation_response_result": {
            "candidate_id": "golden-1",
            "recommendation_served": False,
            "intake_commit_requested": False,
            "is_canonical_truth": False,
        },
        "non_serve_flags": dict(FALSE_ACTIVATION_FLAGS),
    }


def fake_trace(node: str) -> dict[str, Any]:
    return {"stage": f"recommendation_three_node_{node}", "provider": "fake"}


__all__ = [
    "FakeRecommendationThreeNodeDiagnosticProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
    "fake_offer_output",
    "fake_planning_output",
    "fake_trace",
]
