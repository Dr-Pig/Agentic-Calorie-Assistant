from __future__ import annotations

from typing import Any

from .fooddb_live_artifact_digest import (
    ARTIFACT_DIGEST_ALGORITHM,
    ARTIFACT_DIGEST_SCOPE,
)
from .fooddb_live_runner_evidence import (
    EXPECTED_LIVE_RUNNER_TYPE,
    EXPECTED_PREFLIGHT_TYPE,
    EXPECTED_ROUTER_TYPE,
)

_CLEAR_PREFLIGHT_STATUS = "clear_for_grokfast_fooddb_packet_live_diagnostic"
_PASS_STATUS = "pass"


def is_fooddb_live_runner_evidence_healthy(evidence: dict[str, Any]) -> bool:
    return (
        evidence.get("present") is True
        and evidence.get("preflight_artifact_type") == EXPECTED_PREFLIGHT_TYPE
        and evidence.get("preflight_status") == _CLEAR_PREFLIGHT_STATUS
        and evidence.get("preflight_clear_to_run_live_diagnostic") is True
        and evidence.get("preflight_artifact_digest_algorithm") == ARTIFACT_DIGEST_ALGORITHM
        and evidence.get("preflight_artifact_digest_scope") == ARTIFACT_DIGEST_SCOPE
        and evidence.get("preflight_artifact_digest_verified") is True
        and evidence.get("preflight_artifact_integrity_clear") is True
        and evidence.get("router_artifact_type") == EXPECTED_ROUTER_TYPE
        and evidence.get("router_status") == _PASS_STATUS
        and evidence.get("router_fail_count") == 0
        and evidence.get("router_artifact_digest_algorithm") == ARTIFACT_DIGEST_ALGORITHM
        and evidence.get("router_artifact_digest_scope") == ARTIFACT_DIGEST_SCOPE
        and evidence.get("router_artifact_digest_verified") is True
        and evidence.get("router_artifact_integrity_clear") is True
        and evidence.get("live_runner_artifact_type") == EXPECTED_LIVE_RUNNER_TYPE
        and evidence.get("live_runner_status") == _PASS_STATUS
        and evidence.get("ready_for_grokfast_fooddb_packet_live_diagnostic") is True
        and evidence.get("ready_for_runtime_truth") is False
        and evidence.get("live_runner_artifact_digest_algorithm") == ARTIFACT_DIGEST_ALGORITHM
        and evidence.get("live_runner_artifact_digest_scope") == ARTIFACT_DIGEST_SCOPE
        and evidence.get("live_runner_artifact_digest_verified") is True
        and evidence.get("live_runner_artifact_integrity_clear") is True
    )


__all__ = ["is_fooddb_live_runner_evidence_healthy"]
