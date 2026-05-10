from __future__ import annotations

from typing import Any

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.llm_node_fake_provider"
)


class FakeAdvancedShadowLLMNodeProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-advanced-shadow-llm-node", "configured": True}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = dict(kwargs.get("user_payload") or {})
        return (
            {
                "node_output_id": "fake-recommendation-offer-synthesis",
                "selected_candidate_id": str(payload.get("selected_candidate_id") or ""),
                "draft_text": "Review the memory-guided option as a chat-first offer.",
                "rationale": "It is tied to accepted shadow memory and stays review-only.",
                "claim_scope": "advanced_shadow_llm_node_diagnostic_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "reason_codes": ["chat_first", "memory_guided", "review_only"],
            },
            {"stage": "advanced_shadow_llm_node_diagnostic", "provider": "fake"},
        )


__all__ = ["FakeAdvancedShadowLLMNodeProvider", "SIDECAR_ACTIVATION_CONTRACT"]
