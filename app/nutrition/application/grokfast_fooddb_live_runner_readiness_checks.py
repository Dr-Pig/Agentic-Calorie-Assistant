from __future__ import annotations

from typing import Any

from .grokfast_fooddb_diagnostic_preflight import (
    is_grokfast_fooddb_preflight_clear,
)

EXPECTED_FOODDB_PREFLIGHT_ARTIFACT = (
    "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1"
)
EXPECTED_ROUTER_READINESS_ARTIFACT = (
    "accurate_intake_food_evidence_retriever_router_readiness_v1"
)
EXPECTED_LIVE_RUNNER_READINESS_ARTIFACT = (
    "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1"
)
EXPECTED_ROUTER_NEXT_REQUIRED_SLICE = "inspect_websearch_status_packet"
EXPECTED_LIVE_NEXT_REQUIRED_SLICE = "run_explicit_grokfast_fooddb_packet_live_diagnostic"


def readiness_source_refs(
    preflight_artifact: dict[str, Any],
    router_readiness_artifact: dict[str, Any],
) -> dict[str, Any]:
    router_summary = _summary(router_readiness_artifact)
    return {
        "preflight_artifact_type": preflight_artifact.get("artifact_type"),
        "preflight_status": preflight_artifact.get("status"),
        "router_readiness_artifact_type": router_readiness_artifact.get("artifact_type"),
        "router_readiness_status": router_readiness_artifact.get("status"),
        "router_fail_count": int(router_summary.get("fail_count", 0) or 0),
        "router_next_required_slice": router_summary.get("next_required_slice"),
        "router_exact_brand_websearch_ready": router_summary.get(
            "exact_brand_websearch_ready"
        )
        is True,
        "router_websearch_status_gate_present": router_summary.get(
            "websearch_status_gate_present"
        )
        is True,
    }


def input_artifact_blockers(
    *,
    preflight_artifact: dict[str, Any],
    router_readiness_artifact: dict[str, Any],
) -> list[str]:
    return sorted(
        set(
            [
                *_preflight_blockers(preflight_artifact),
                *_router_readiness_blockers(router_readiness_artifact),
            ]
        )
    )


def live_runner_readiness_input_blockers(
    *,
    readiness_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
    router_readiness_artifact: dict[str, Any],
) -> list[str]:
    blockers = [
        *input_artifact_blockers(
            preflight_artifact=preflight_artifact,
            router_readiness_artifact=router_readiness_artifact,
        )
    ]
    if readiness_artifact.get("artifact_type") != EXPECTED_LIVE_RUNNER_READINESS_ARTIFACT:
        blockers.append("unsupported_fooddb_live_runner_readiness_artifact")
        return sorted(set(blockers))
    if not is_grokfast_fooddb_live_runner_readiness_clear(readiness_artifact):
        blockers.append("fooddb_live_runner_readiness_packet_not_clear")
    refs = readiness_source_refs(preflight_artifact, router_readiness_artifact)
    source_refs = readiness_artifact.get("source_refs")
    if not isinstance(source_refs, dict):
        blockers.append("fooddb_live_runner_readiness_source_refs_missing")
        return sorted(set(blockers))
    for key, expected in refs.items():
        if source_refs.get(key) != expected:
            blockers.append(f"fooddb_live_runner_readiness_source_ref_mismatch:{key}")
    return sorted(set(blockers))


def is_grokfast_fooddb_live_runner_readiness_clear(artifact: dict[str, Any]) -> bool:
    if artifact.get("artifact_type") != EXPECTED_LIVE_RUNNER_READINESS_ARTIFACT:
        return False
    if artifact.get("status") != "pass":
        return False
    if artifact.get("ready_for_grokfast_fooddb_packet_live_diagnostic") is not True:
        return False
    if artifact.get("ready_for_runtime_truth") is not False:
        return False
    if artifact.get("runtime_truth_changed") is not False:
        return False
    if artifact.get("runtime_mutation_allowed") is not False:
        return False
    if artifact.get("manager_context_changed") is not False:
        return False
    if artifact.get("shared_contract_changed") is not False:
        return False
    if artifact.get("packetizer_format_changed") is not False:
        return False
    if artifact.get("live_provider_used") is not False:
        return False
    if artifact.get("live_websearch_used") is not False:
        return False
    if artifact.get("readiness_claimed") is not False:
        return False
    if artifact.get("provider_readiness_checked") is not False:
        return False
    if artifact.get("next_required_slice") != EXPECTED_LIVE_NEXT_REQUIRED_SLICE:
        return False
    summary = _summary(artifact)
    if summary.get("preflight_status") != "clear_for_grokfast_fooddb_packet_live_diagnostic":
        return False
    if summary.get("router_readiness_status") != "pass":
        return False
    if int(summary.get("router_readiness_fail_count", 0) or 0) != 0:
        return False
    runner_contract = artifact.get("runner_contract")
    if not isinstance(runner_contract, dict):
        return False
    expected_flags = {
        "requires_explicit_allow_live_flag": True,
        "requires_clear_fooddb_preflight": True,
        "requires_clear_retriever_router_readiness": True,
        "requires_clear_live_runner_readiness_packet": True,
        "live_call_allowed_by_this_artifact": False,
        "ledger_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
    }
    return all(runner_contract.get(key) is value for key, value in expected_flags.items())


def _preflight_blockers(preflight: dict[str, Any]) -> list[str]:
    if preflight.get("artifact_type") != EXPECTED_FOODDB_PREFLIGHT_ARTIFACT:
        return ["unsupported_fooddb_grokfast_preflight_artifact"]
    if not is_grokfast_fooddb_preflight_clear(preflight):
        return ["fooddb_grokfast_preflight_not_clear"]
    return []


def _router_readiness_blockers(router_readiness: dict[str, Any]) -> list[str]:
    if router_readiness.get("artifact_type") != EXPECTED_ROUTER_READINESS_ARTIFACT:
        return ["unsupported_food_evidence_retriever_router_readiness_artifact"]
    blockers: list[str] = []
    if router_readiness.get("status") != "pass":
        blockers.append("food_evidence_retriever_router_readiness_not_pass")
    if router_readiness.get("runtime_truth_changed") is not False:
        blockers.append("food_evidence_retriever_router_readiness_changed_runtime_truth")
    if router_readiness.get("mutation_changed") is not False:
        blockers.append("food_evidence_retriever_router_readiness_changed_mutation")
    if router_readiness.get("shared_contract_changed") is not False:
        blockers.append("food_evidence_retriever_router_readiness_changed_shared_contract")
    if router_readiness.get("manager_context_changed") is not False:
        blockers.append("food_evidence_retriever_router_readiness_changed_manager_context")
    if router_readiness.get("live_provider_used") is not False:
        blockers.append("food_evidence_retriever_router_readiness_used_live_provider")
    if router_readiness.get("live_websearch_used") is not False:
        blockers.append("food_evidence_retriever_router_readiness_used_live_websearch")
    if router_readiness.get("readiness_claimed") is not False:
        blockers.append("food_evidence_retriever_router_readiness_claimed_readiness")
    summary = _summary(router_readiness)
    if int(summary.get("fail_count", 0) or 0) != 0:
        blockers.append("food_evidence_retriever_router_readiness_has_failures")
    if summary.get("next_required_slice") != EXPECTED_ROUTER_NEXT_REQUIRED_SLICE:
        blockers.append("food_evidence_retriever_router_readiness_next_slice_mismatch")
    return blockers


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary")
    return dict(summary) if isinstance(summary, dict) else {}


__all__ = [
    "EXPECTED_LIVE_NEXT_REQUIRED_SLICE",
    "EXPECTED_LIVE_RUNNER_READINESS_ARTIFACT",
    "EXPECTED_ROUTER_NEXT_REQUIRED_SLICE",
    "input_artifact_blockers",
    "is_grokfast_fooddb_live_runner_readiness_clear",
    "live_runner_readiness_input_blockers",
    "readiness_source_refs",
]
