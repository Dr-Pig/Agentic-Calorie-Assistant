from __future__ import annotations

from typing import Any

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.live_bundle_fake_providers"
)


class FakeRecommendationCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-recommendation-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "candidate_id": "golden-1",
                "draft_prompt": "Consider the selected option as a low-friction choice.",
                "reason_summary": "It matches the shadow candidate signals and remains review-only.",
                "claim_scope": "diagnostic_copy_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "reason_codes": ["review_only"],
            },
            {"stage": "advanced_shadow_recommendation_copy_live_diagnostic", "provider": "fake"},
        )


class FakeRescueCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-rescue-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "proposal_headline": "Recover the rest of the week with a small adjustment.",
                "proposal_summary": "Use a review-only offset and keep the tone neutral.",
                "coaching_frame": "Frame this as planning, not punishment.",
                "recommended_days": 2,
                "daily_kcal_adjustment": -150,
                "cap_mode": "standard_15_percent",
                "special_posture": "standard_spread",
                "claim_scope": "diagnostic_copy_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "reason_codes": ["review_only"],
            },
            {"stage": "advanced_shadow_rescue_copy_live_diagnostic", "provider": "fake"},
        )


class FakeProactiveCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-proactive-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "draft_chat_message": "A review-only prompt could be useful later.",
                "reason_summary": "It has no-send controls and a clear next signal.",
                "false_positive_silence_case": "Stay silent if the user already handled it.",
                "next_signal": "Wait for a new app-open or material budget signal.",
                "claim_scope": "diagnostic_copy_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "scheduler_request": False,
                "notification_request": False,
                "reason_codes": ["chat_first", "review_only"],
            },
            {"stage": "advanced_shadow_proactive_copy_live_diagnostic", "provider": "fake"},
        )


__all__ = [
    "FakeProactiveCopyDiagnosticProvider",
    "FakeRecommendationCopyDiagnosticProvider",
    "FakeRescueCopyDiagnosticProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
]
