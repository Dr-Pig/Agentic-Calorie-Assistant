from __future__ import annotations

from typing import Any

from app.nutrition.application.websearch_manager_output_evaluation import (
    allowed_candidate_refs,
)
from app.nutrition.application.websearch_manager_output_policy import (
    WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE,
)


def build_fixture_websearch_manager_outputs(*, packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet_case in packet_artifact.get("cases") or []:
        if not isinstance(packet_case, dict):
            continue
        manager_packet = packet_case.get("manager_evidence_packet")
        if not isinstance(manager_packet, dict):
            continue
        candidate_refs = allowed_candidate_refs(manager_packet)
        expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
        if expected_behavior == "candidate_review_or_later_exact_card_promotion_path":
            manager_output = {
                "manager_action": "final",
                "final_action": "no_commit",
                "workflow_effect": "source_candidate_review",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "text": "WebSearch returned a candidate only; exact-card promotion is required before kcal use.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        elif expected_behavior == "ask_followup_or_keep_candidate_pending":
            manager_output = {
                "manager_action": "final",
                "final_action": "ask_followup",
                "workflow_effect": "pause_for_clarification",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "followup_question": "Please confirm the exact menu item or size.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        else:
            manager_output = {
                "manager_action": "final",
                "final_action": "no_commit",
                "workflow_effect": "no_mutation",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "text": "WebSearch candidate is not sufficient for nutrition truth.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        outputs.append(
            {
                "case_id": packet_case.get("case_id"),
                "manager_output": manager_output,
                "provider_trace": dict(WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE),
            }
        )
    return outputs


__all__ = ["build_fixture_websearch_manager_outputs"]
