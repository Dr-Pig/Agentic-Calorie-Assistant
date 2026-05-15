from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from .fooddb_websearch_no_runtime_selection import (
    build_default_fooddb_websearch_no_runtime_inputs,
    select_fooddb_websearch_no_runtime_next_required_slice,
)
from .fooddb_websearch_no_runtime_wall_policy import FORBIDDEN_TRUE_KEYS
from .fooddb_websearch_no_runtime_wall_scan import (
    forbidden_paths,
    stable_unique,
)


def build_default_fooddb_websearch_no_runtime_wall() -> dict[str, Any]:
    defaults = build_default_fooddb_websearch_no_runtime_inputs()
    return build_fooddb_websearch_no_runtime_wall(artifacts=defaults["artifacts"])


def build_fooddb_websearch_no_runtime_wall(
    *,
    artifacts: Iterable[dict[str, Any]],
    next_required_slice: str | None = None,
) -> dict[str, Any]:
    artifact_list = list(artifacts)
    artifact_results = [_artifact_result(artifact) for artifact in artifact_list]
    blockers = [
        blocker
        for result in artifact_results
        for blocker in result["blockers"]
    ]
    clear = not blockers
    resolved_next_required_slice = next_required_slice or select_fooddb_websearch_no_runtime_next_required_slice(
        wall_clear=clear,
        fooddb_status_packet=_artifact_with_type(
            artifact_list,
            "accurate_intake_fooddb_evidence_status_packet_v1",
        ),
        websearch_status_packet=_artifact_with_type(
            artifact_list,
            "accurate_intake_websearch_candidate_lane_status_packet_v1",
        ),
    )
    return {
        "artifact_type": "accurate_intake_fooddb_websearch_no_runtime_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_no_runtime_wall_only",
        "claim_scope": "fooddb_websearch_candidate_preflight_report_no_runtime_effect_wall",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "artifact_results": artifact_results,
        "summary": {
            "artifact_count": len(artifact_results),
            "pass_count": sum(1 for result in artifact_results if result["status"] == "pass"),
            "blocked_count": sum(1 for result in artifact_results if result["status"] != "pass"),
            "runtime_truth_leak_count": sum(
                1
                for result in artifact_results
                for blocker in result["blockers"]
                if "runtime_truth" in blocker
            ),
            "live_or_readiness_leak_count": sum(
                1
                for result in artifact_results
                for blocker in result["blockers"]
                if "live_" in blocker or "readiness" in blocker or "self_use" in blocker
            ),
        },
        "policy": {
            "deterministic_wall_scope": "candidate_preflight_status_report_artifacts",
            "allowed_fooddb_runtime_anchor_presence": (
                "not_evaluated_here; this wall checks effect/claim leakage only"
            ),
            "websearch_candidate_runtime_truth": "forbidden",
            "exact_card_candidate_runtime_truth": "forbidden",
            "mutation": "forbidden",
            "live_calls": "forbidden",
            "readiness_claims": "forbidden",
        },
        "next_required_slice": resolved_next_required_slice,
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_websearch_runtime_truth",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _artifact_result(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(artifact.get("artifact_type") or "unknown_artifact")
    paths = stable_unique(forbidden_paths(artifact, artifact_type=artifact_type))
    blockers = [f"{artifact_type}:{path}" for path in paths]
    return {
        "artifact_type": artifact_type,
        "status": "pass" if not blockers else "blocked",
        "classification": artifact.get("classification"),
        "claim_scope": artifact.get("claim_scope"),
        "blockers": blockers,
        "checked_forbidden_key_count": len(FORBIDDEN_TRUE_KEYS),
        "checked_forbidden_pattern_policy": (
            "status_blocker_count_suffix_and_candidate_lane_fail_closed"
        ),
    }

def _artifact_with_type(
    artifacts: Iterable[dict[str, Any]],
    artifact_type: str,
) -> dict[str, Any] | None:
    for artifact in artifacts:
        if str(artifact.get("artifact_type") or "") == artifact_type:
            return artifact
    return None

def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FORBIDDEN_TRUE_KEYS",
    "build_default_fooddb_websearch_no_runtime_wall",
    "build_fooddb_websearch_no_runtime_wall",
]
