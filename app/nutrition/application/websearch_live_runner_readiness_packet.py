from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .grokfast_websearch_packet_profile import GROKFAST_WEBSEARCH_PACKET_PROFILE
from .websearch_live_runner_readiness_checks import (
    input_artifact_blockers,
    is_websearch_live_runner_readiness_clear,
    live_runner_readiness_input_blockers,
    readiness_source_refs,
    review_packet_count,
)


def build_websearch_live_runner_readiness_packet(
    *,
    review_packet_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
    exact_candidate_chain_status_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers = input_artifact_blockers(
        review_packet_artifact=review_packet_artifact,
        preflight_artifact=preflight_artifact,
        exact_candidate_chain_status_artifact=exact_candidate_chain_status_artifact,
    )
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_live_runner_readiness_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_live_runner_readiness_only",
        "claim_scope": "websearch_live_runner_pre_provider_call_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "ready_for_grokfast_websearch_packet_live_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "live_extract_used": False,
        "readiness_claimed": False,
        "provider_readiness_checked": False,
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "source_refs": readiness_source_refs(
            review_packet_artifact,
            preflight_artifact,
            exact_candidate_chain_status_artifact,
        ),
        "summary": {
            "review_packet_count": review_packet_count(review_packet_artifact),
            "preflight_status": preflight_artifact.get("status"),
            "chain_status": exact_candidate_chain_status_artifact.get("status"),
            "provider_configuration_status": "not_checked_until_live_invocation",
        },
        "runner_contract": {
            "requires_explicit_allow_live_flag": True,
            "requires_clear_live_extract_preflight": True,
            "requires_clear_exact_candidate_chain_status": True,
            "requires_clear_live_runner_readiness_packet": True,
            "live_call_allowed_by_this_artifact": False,
            "ledger_mutation_allowed": False,
            "websearch_runtime_truth_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "next_required_slice": (
            "run_explicit_grokfast_websearch_packet_live_diagnostic"
            if clear
            else "inspect_websearch_live_runner_readiness_blockers"
        ),
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_live_runner_readiness_packet",
    "is_websearch_live_runner_readiness_clear",
    "live_runner_readiness_input_blockers",
]
