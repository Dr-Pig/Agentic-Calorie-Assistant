from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.candidate_extraction import (
    _build_candidates,
    _build_context_value_items,
)
from app.memory.application.long_term_context_shadow.contracts import (
    ARTIFACT_CONSUMER_CATALOG,
    CHAT_TRACE_SECTION_ALIASES,
    DOGFOOD_EXPORT_SECTIONS,
    SHADOW_NON_CLAIM_FLAGS,
    artifact_review_contract,
    build_artifact_registry_manifest,
)
from app.memory.application.long_term_context_shadow.fixture_reader import (
    _normalize_dogfood_export_payload,
)
from app.memory.application.long_term_context_shadow.future_artifacts import (
    build_future_shadow_artifacts,
)
from app.memory.application.long_term_context_shadow.review_artifacts import (
    build_review_artifacts,
)
from app.memory.application.long_term_context_shadow.shadow_evaluators import (
    build_evaluator_artifacts,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow_lab"
)


def build_shadow_lab_artifacts(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    fixture = _normalize_dogfood_export_payload(fixture_payload)
    candidates = _build_candidates(fixture)
    context_items = _build_context_value_items(candidates)

    artifacts = build_review_artifacts(fixture, candidates, context_items)
    artifacts.update(build_evaluator_artifacts(fixture, candidates))
    artifacts.update(build_future_shadow_artifacts(fixture, candidates))
    artifacts["artifact_registry_manifest"] = build_artifact_registry_manifest(
        fixture,
        artifacts,
    )
    return artifacts


__all__ = [
    "ARTIFACT_CONSUMER_CATALOG",
    "CHAT_TRACE_SECTION_ALIASES",
    "DOGFOOD_EXPORT_SECTIONS",
    "SHADOW_NON_CLAIM_FLAGS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "artifact_review_contract",
    "build_artifact_registry_manifest",
    "build_shadow_lab_artifacts",
]
