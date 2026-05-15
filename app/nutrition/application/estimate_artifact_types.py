from __future__ import annotations

from dataclasses import dataclass

from app.composition.request_runtime_context import RequestRuntimeContext
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import EstimatePayload


@dataclass(frozen=True)
class EstimatedNutritionArtifact:
    request: EstimateRequest
    runtime_context: RequestRuntimeContext
    payload: EstimatePayload
