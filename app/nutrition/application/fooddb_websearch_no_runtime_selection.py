from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .exact_evidence_lane_status_packet import build_exact_evidence_lane_status_packet
from .fooddb_activation_gap_report import build_fooddb_activation_gap_report
from .fooddb_evidence_status_packet import build_fooddb_evidence_status_packet
from .fooddb_integration_readiness_matrix import build_fooddb_integration_readiness_matrix
from .fooddb_runtime_anchor_batch import (
    build_fooddb_runtime_coverage_matrix,
    build_fooddb_status_packet,
    build_internal_seed_runtime_anchor_batch,
)
from .websearch_cache_rate_license_wall import build_websearch_cache_rate_license_wall
from .websearch_candidate_lane_status_packet import build_websearch_candidate_lane_status_packet
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_exact_candidate_review_packet import build_websearch_exact_candidate_review_packet
from .websearch_extract_result_candidate_smoke import build_websearch_extract_result_candidate_smoke
from .websearch_grokfast_live_diagnostic_case_matrix import (
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from .websearch_live_extract_preflight import build_websearch_live_extract_preflight
from .websearch_selected_extract_packet_smoke import build_websearch_selected_extract_packet_smoke
from .websearch_source_adapter_guard import build_websearch_source_adapter_guard
from .websearch_source_policy import build_websearch_source_policy_artifact

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INSPECT_BLOCKERS = "inspect_fooddb_websearch_no_runtime_wall_blockers"
_FALLBACK_LIVE_SLICE = "grokfast_fooddb_packet_live_diagnostic"
_FOODDB_WEBSEARCH_HANDOFF = "grokfast_websearch_packet_live_diagnostic"


def build_default_fooddb_websearch_no_runtime_inputs() -> dict[str, Any]:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    exact_readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=exact_lane
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract
    )
    exact_review = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    fooddb_status_artifacts, fooddb_status_packet = _default_fooddb_status_artifacts()
    websearch_status_packet = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=fooddb_status_packet
    )
    artifacts = (
        *fooddb_status_artifacts,
        build_fooddb_integration_readiness_matrix(),
        build_websearch_source_policy_artifact(),
        build_websearch_source_adapter_guard(),
        build_websearch_cache_rate_license_wall(),
        build_websearch_candidate_pipeline_diagnostic(),
        build_websearch_candidate_packet_smoke(),
        selected_extract,
        extract_result,
        exact_review,
        build_websearch_grokfast_live_diagnostic_case_matrix_artifact(),
        build_websearch_live_extract_preflight(
            exact_review_packet_artifact=exact_review,
        ),
        exact_lane,
        exact_readiness,
        websearch_status_packet,
        build_exact_evidence_lane_status_packet(
            websearch_status_packet=websearch_status_packet
        ),
    )
    return {
        "artifacts": artifacts,
        "fooddb_status_packet": fooddb_status_packet,
        "websearch_status_packet": websearch_status_packet,
    }


def select_fooddb_websearch_no_runtime_next_required_slice(
    *,
    wall_clear: bool,
    fooddb_status_packet: dict[str, Any] | None = None,
    websearch_status_packet: dict[str, Any] | None = None,
) -> str:
    if not wall_clear:
        return _INSPECT_BLOCKERS
    fooddb_next = _first_next_required_slice(fooddb_status_packet)
    if fooddb_next and fooddb_next != _FOODDB_WEBSEARCH_HANDOFF:
        return fooddb_next
    websearch_next = _first_next_required_slice(websearch_status_packet)
    if websearch_next:
        return websearch_next
    if fooddb_next:
        return fooddb_next
    return _FALLBACK_LIVE_SLICE


def _default_fooddb_status_artifacts() -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    small_anchor_payload = _read_repo_json("app/knowledge/small_anchor_store_tw.json")
    tfda_source_payload = _read_repo_json("app/knowledge/tfda_per100g_source_evidence_tw.json")
    exact_card_payload = _read_repo_json("app/knowledge/exact_item_cards_tw.json")
    coverage_matrix = build_fooddb_runtime_coverage_matrix(
        small_anchor_payload=small_anchor_payload
    )
    runtime_batch = build_internal_seed_runtime_anchor_batch(
        small_anchor_payload=small_anchor_payload
    )
    fooddb_status_packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=small_anchor_payload,
        tfda_source_payload=tfda_source_payload,
        exact_card_payload=exact_card_payload,
    )
    artifacts = (
        fooddb_status_packet,
        build_fooddb_activation_gap_report(
            small_anchor_payload=small_anchor_payload,
            tfda_source_payload=tfda_source_payload,
            exact_card_payload=exact_card_payload,
        ),
        build_fooddb_status_packet(
            small_anchor_payload=small_anchor_payload,
            coverage_matrix=coverage_matrix,
            runtime_batch=runtime_batch,
        ),
    )
    return artifacts, fooddb_status_packet


def _read_repo_json(relative_path: str) -> dict[str, Any]:
    raw = (_REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"expected_object_json:{relative_path}")
    return payload


def _first_next_required_slice(artifact: dict[str, Any] | None) -> str | None:
    if not isinstance(artifact, dict):
        return None
    next_required_slices = artifact.get("next_required_slices")
    if isinstance(next_required_slices, list) and next_required_slices:
        text = str(next_required_slices[0] or "").strip()
        return text or None
    next_required_slice = str(artifact.get("next_required_slice") or "").strip()
    return next_required_slice or None


__all__ = [
    "build_default_fooddb_websearch_no_runtime_inputs",
    "select_fooddb_websearch_no_runtime_next_required_slice",
]
