from __future__ import annotations

from typing import Any


GROKFAST_FOODDB_PACKET_PROFILE = {
    "provider_profile_id": "builderspace-grok-4-fast-fooddb-packet-smoke",
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
    "no_kimi_call",
    "no_websearch_runtime_truth",
]

FOODDB_PACKET_MANAGER_REQUIRED_FIELDS = (
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


def packet_artifact_case_ids(packet_artifact: dict[str, Any]) -> list[str]:
    return [
        str(case.get("case_id") or "").strip()
        for case in packet_artifact.get("cases") or []
        if isinstance(case, dict) and str(case.get("case_id") or "").strip()
    ]


__all__ = [
    "FOODDB_PACKET_MANAGER_REQUIRED_FIELDS",
    "GROKFAST_FOODDB_PACKET_PROFILE",
    "NON_CLAIMS",
    "packet_artifact_case_ids",
]
