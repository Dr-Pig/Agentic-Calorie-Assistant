from __future__ import annotations

from typing import Any


class BodyObservationManagerFixtureProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"configured": True, "provider": "body_observation_fixture"}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(payload.get("available_tools") or []),
                "tool_results": list(payload.get("tool_results") or []),
                "round_index": payload.get("round_index"),
            }
        )
        if int(payload.get("round_index") or 0) == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {
                            "name": "body.record_observation",
                            "arguments": {"observation_type": "weight", "value": 70.0, "unit": "kg"},
                        }
                    ],
                },
                {"source": "body_observation_fixture"},
            )
        return (
            {
                "manager_action": "final",
                "intent": "body_observation",
                "intent_type": "body_observation",
                "final_action": "answer_only",
                "workflow_effect": "record_weight",
                "target_attachment": {"mode": "body_observation_recorded"},
                "exactness": "deterministic_fixture",
                "confidence": "high",
                "evidence_posture": "write_only_domain_mutation",
                "repair_ack": False,
                "answer_contract": {"reply_text": "Recorded weight 70.0 kg. Body plan was not changed."},
                "response_summary": "record_weight",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "mutation_result",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "body_observation",
                    "target_attachment": {"mode": "body_observation_recorded"},
                    "workflow_effect": "record_weight",
                    "final_action_candidate": "answer_only",
                    "followup_posture": "none",
                    "mutation_intent_candidate": "body_observation_write",
                    "semantic_owner": "manager",
                },
                "tool_calls": [],
            },
            {"source": "body_observation_fixture"},
        )
