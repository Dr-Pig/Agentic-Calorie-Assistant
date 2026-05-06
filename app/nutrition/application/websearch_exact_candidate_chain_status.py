from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .websearch_exact_candidate_chain_checks import (
    artifact_blockers,
    chain_blockers,
    chain_proof,
    extract_candidates,
    preflight_refs,
    review_packets,
    runtime_truth_count,
    selected_packets,
)
from .websearch_exact_candidate_review_packet import (
    build_websearch_exact_candidate_review_packet,
)
from .websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from .websearch_live_extract_preflight import build_websearch_live_extract_preflight
from .websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def build_websearch_exact_candidate_chain_status(
    *,
    selected_extract_artifact: dict[str, Any] | None = None,
    extract_result_artifact: dict[str, Any] | None = None,
    exact_review_packet_artifact: dict[str, Any] | None = None,
    preflight_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = (
        _default_selected_extract()
        if selected_extract_artifact is None
        else selected_extract_artifact
    )
    extract = extract_result_artifact
    if extract is None:
        extract = build_websearch_extract_result_candidate_smoke(
            selected_extract_artifact=selected
        )
    review = exact_review_packet_artifact
    if review is None:
        review = build_websearch_exact_candidate_review_packet(extract_result_artifact=extract)
    preflight = preflight_artifact
    if preflight is None:
        preflight = build_websearch_live_extract_preflight(exact_review_packet_artifact=review)
    blockers = [
        *artifact_blockers("selected_extract", selected),
        *artifact_blockers("extract_result", extract),
        *artifact_blockers("exact_review_packet", review),
        *artifact_blockers("preflight", preflight),
        *chain_blockers(selected, extract, review, preflight),
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_exact_candidate_chain_status_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_exact_candidate_chain_status_only",
        "claim_scope": "websearch_exact_candidate_chain_readiness_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "readiness_claimed": False,
        "ready_for_live_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "source_artifacts": {
            "selected_extract_artifact_type": selected.get("artifact_type"),
            "extract_result_artifact_type": extract.get("artifact_type"),
            "exact_review_packet_artifact_type": review.get("artifact_type"),
            "preflight_artifact_type": preflight.get("artifact_type"),
        },
        "summary": {
            "selected_extract_packet_count": len(selected_packets(selected)),
            "extract_result_candidate_count": len(extract_candidates(extract)),
            "review_packet_count": len(review_packets(review)),
            "preflight_review_ref_count": len(preflight_refs(preflight)),
            "runtime_truth_allowed_count": runtime_truth_count(selected, extract, review),
            "ready_for_runtime_truth_count": 0,
        },
        "chain_proof": chain_proof(selected, extract, review, preflight),
        "next_required_slice": (
            "grokfast_websearch_packet_live_diagnostic"
            if clear
            else "inspect_websearch_exact_candidate_chain_status"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _default_selected_extract() -> dict[str, Any]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    return build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_candidate_chain_status"]
