from __future__ import annotations

from typing import Any, Callable


GROKFAST_WEBSEARCH_PACKET_PROFILE = {
    "provider_profile_id": "builderspace-grok-4-fast-websearch-packet-smoke",
    "provider": "builderspace",
    "model": "grok-4-fast",
    "provider_profile_role": "live_diagnostic_probe",
    "cost_tier": "low",
    "production_selected": False,
    "readiness_owner": False,
}

NON_CLAIMS = [
    "no_readiness_claim",
    "no_production_model_selection",
    "no_self_use_approval",
    "no_runtime_mutation",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_kimi_call",
    "no_websearch_runtime_truth",
]

WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS = (
    "manager_action",
    "response_mode",
    "intent",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
    "operations",
    "answer_contract",
)

ManagerContractValidator = Callable[[dict[str, Any], dict[str, Any]], list[str]]


__all__ = [
    "GROKFAST_WEBSEARCH_PACKET_PROFILE",
    "ManagerContractValidator",
    "NON_CLAIMS",
    "WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS",
]
