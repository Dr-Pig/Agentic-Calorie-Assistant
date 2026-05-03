from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.composition.request_runtime_context import RequestRuntimeContext
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import EstimatePayload


@dataclass(frozen=True)
class TargetEvidenceArtifact:
    """Evidence artifact for target resolution, not nutrition estimation."""

    request: EstimateRequest
    runtime_context: RequestRuntimeContext
    payload: EstimatePayload


def payload_is_target_evidence(payload: Any | None) -> bool:
    trace_contract = dict(getattr(payload, "trace_contract", None) or {})
    target_contract = dict(trace_contract.get("target_evidence_contract") or {})
    return str(target_contract.get("evidence_type") or "") == "target_evidence"


def artifact_is_target_evidence(artifact: Any | None) -> bool:
    if isinstance(artifact, TargetEvidenceArtifact):
        return True
    return payload_is_target_evidence(getattr(artifact, "payload", None))


__all__ = ["TargetEvidenceArtifact", "artifact_is_target_evidence", "payload_is_target_evidence"]
