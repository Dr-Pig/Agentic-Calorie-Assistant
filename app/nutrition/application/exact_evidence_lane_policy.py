from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_evidence_lane_cases import build_exact_evidence_lane_policy_cases


def build_exact_evidence_lane_policy_artifact() -> dict[str, Any]:
    cases = build_exact_evidence_lane_policy_cases()
    return {
        "artifact_type": "accurate_intake_exact_evidence_lane_policy_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "offline_exact_lane_policy_only",
        "claim_scope": "deterministic_exact_lane_order_and_boundary",
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "packetizer_format_changed": False,
        "manager_context_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "local_exact_preferred_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "local_exact_seed_support_only"
            ),
            "websearch_candidate_review_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "websearch_candidate_review"
            ),
            "no_exact_evidence_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "no_exact_evidence"
            ),
            "exact_card_staging_candidate_count": sum(
                case["exact_card_staging"]["candidate_count"] for case in cases
            ),
        },
        "lane_order": [
            "local_exact_seed_support_only",
            "websearch_candidate_review",
            "no_exact_evidence",
        ],
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_packet_ready_truth",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_exact_evidence_lane_policy_artifact"]
