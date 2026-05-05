from __future__ import annotations

from typing import Any

from app.nutrition.application.grokfast_websearch_packet_profile import (
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
)


def build_fixture_manager_outputs(*, review_packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet in review_packet_artifact.get("review_packets") or []:
        if not isinstance(packet, dict):
            continue
        outputs.append(
            {
                "packet_id": packet.get("packet_id"),
                "manager_output": {
                    "manager_action": "final",
                    "response_mode": "info_answer",
                    "intent": "query_food_calories",
                    "final_action": "answer_only",
                    "workflow_effect": "no_mutation_review_candidate_only",
                    "target_attachment": {},
                    "exactness": "candidate_only",
                    "confidence": "medium",
                    "evidence_posture": "candidate_review_only",
                    "repair_ack": False,
                    "operations": [],
                    "item_results": [],
                    "evidence_used": [packet.get("packet_id"), packet.get("source_url")],
                    "answer_contract": {
                        "text": "WebSearch packet is an exact-card review candidate only; approval is required before runtime use."
                    },
                    "semantic_decision": {
                        "semantic_authority": "deterministic_fake_provider",
                        "current_turn_intent": "answer_query",
                        "target_attachment": {},
                        "workflow_effect": "no_mutation_review_candidate_only",
                        "final_action_candidate": "answer_only",
                        "estimation_posture": "review_candidate_only",
                        "followup_posture": "none",
                        "followup_question": None,
                        "followup_targets": [],
                        "mutation_intent_candidate": "no_mutation",
                        "uncertainty_posture": "candidate_only",
                        "source": "fixture_websearch_packet_diagnostic",
                        "semantic_owner": "deterministic_fake_provider",
                        "deterministic_role": "schema_fixture_only",
                    },
                },
                "provider_trace": {
                    "fixture_provider": True,
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                },
            }
        )
    return outputs


__all__ = ["build_fixture_manager_outputs"]
