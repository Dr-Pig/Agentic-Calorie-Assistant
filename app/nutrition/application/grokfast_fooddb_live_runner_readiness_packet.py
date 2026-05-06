from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .grokfast_fooddb_live_runner_readiness_checks import (
    EXPECTED_LIVE_NEXT_REQUIRED_SLICE,
    input_artifact_blockers,
    is_grokfast_fooddb_live_runner_readiness_clear,
    readiness_source_refs,
)
from .grokfast_fooddb_packet_smoke import GROKFAST_FOODDB_PACKET_PROFILE


def build_grokfast_fooddb_live_runner_readiness_packet(
    *,
    preflight_artifact: dict[str, Any],
    router_readiness_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers = input_artifact_blockers(
        preflight_artifact=preflight_artifact,
        router_readiness_artifact=router_readiness_artifact,
    )
    clear = not blockers
    router_summary = dict(router_readiness_artifact.get("summary") or {})
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_fooddb_live_runner_readiness_only",
        "claim_scope": "fooddb_live_runner_pre_provider_call_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "ready_for_grokfast_fooddb_packet_live_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "provider_readiness_checked": False,
        "provider_profile": dict(GROKFAST_FOODDB_PACKET_PROFILE),
        "source_refs": readiness_source_refs(
            preflight_artifact,
            router_readiness_artifact,
        ),
        "summary": {
            "preflight_status": preflight_artifact.get("status"),
            "router_readiness_status": router_readiness_artifact.get("status"),
            "router_readiness_fail_count": int(
                router_summary.get("fail_count", 0) or 0
            ),
            "router_next_required_slice": router_summary.get("next_required_slice"),
            "router_exact_brand_websearch_ready": router_summary.get(
                "exact_brand_websearch_ready"
            )
            is True,
            "provider_configuration_status": "not_checked_until_live_invocation",
        },
        "runner_contract": {
            "requires_explicit_allow_live_flag": True,
            "requires_clear_fooddb_preflight": True,
            "requires_clear_retriever_router_readiness": True,
            "requires_clear_live_runner_readiness_packet": True,
            "live_call_allowed_by_this_artifact": False,
            "ledger_mutation_allowed": False,
            "websearch_runtime_truth_allowed": False,
        },
        "next_required_slice": (
            EXPECTED_LIVE_NEXT_REQUIRED_SLICE
            if clear
            else "inspect_grokfast_fooddb_live_runner_readiness_blockers"
        ),
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_shared_contract_change",
            "no_packetizer_format_change",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_grokfast_fooddb_live_runner_readiness_packet",
    "is_grokfast_fooddb_live_runner_readiness_clear",
    "input_artifact_blockers",
]
