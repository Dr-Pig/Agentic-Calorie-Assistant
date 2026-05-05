from __future__ import annotations

from typing import Any

from app.nutrition.application.grokfast_websearch_packet_evaluation import (
    allowed_review_packet_refs,
)
from app.nutrition.application.grokfast_websearch_packet_profile import (
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
    WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS,
)


def build_live_manager_payload(*, review_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_scope": "websearch_review_packet_manager_seam_smoke",
        "raw_user_input": review_packet.get("matched_name") or review_packet.get("canonical_name"),
        "websearch_exact_candidate_review_packet": dict(review_packet),
        "allowed_evidence_refs": sorted(allowed_review_packet_refs(review_packet)),
        "instructions": [
            "Return one JSON object matching the active B1 pass-2 manager schema.",
            "Include the required top-level manager fields: manager_action, response_mode, intent, workflow_effect, target_attachment, exactness, confidence, evidence_posture, repair_ack, operations, and answer_contract.",
            "Use manager_action=final, response_mode=info_answer, intent=query_food_calories, final_action=answer_only, target_attachment={}, operations=[].",
            "Use only the provided WebSearch exact-card review packet for source references.",
            "If you include evidence_used, every value must exactly equal one allowed_evidence_refs value; do not add prefixes, policy labels, or paraphrased source ids.",
            "Treat extracted kcal/serving values as review candidates, not runtime truth.",
            "Do not include item_results, kcal_range, likely_kcal, or any user-facing estimate fields.",
            "Do not create an exact card or claim runtime nutrition truth.",
            "Do not mutate or write ledger state.",
            "Return a final answer-only diagnostic decision that states approval is required before runtime use.",
        ],
        "expected_output_contract": {
            "required_top_level_fields": list(WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS),
            "manager_action": "final",
            "response_mode": "info_answer",
            "intent": "query_food_calories",
            "final_action": "answer_only",
            "target_attachment": {},
            "operations": [],
            "forbidden_top_level_fields": ["item_results"],
            "forbidden_nested_fields": ["kcal_range", "likely_kcal"],
            "allowed_evidence_refs": sorted(allowed_review_packet_refs(review_packet)),
            "runtime_mutation_allowed": False,
            "runtime_truth_allowed": False,
        },
        "constraints": {
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": "common_commercial_drink",
            "phase_b1_provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
            "websearch_review_packet_smoke": True,
            "runtime_truth_allowed": False,
            "runtime_mutation_allowed": False,
        },
    }


__all__ = ["build_live_manager_payload"]
