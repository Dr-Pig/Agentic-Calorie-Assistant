from __future__ import annotations

from typing import Any


def artifact_blockers(prefix: str, artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    expected_type = _EXPECTED_ARTIFACT_TYPES.get(prefix)
    if expected_type and artifact.get("artifact_type") != expected_type:
        blockers.append(f"{prefix}_artifact_unsupported_type")
    if artifact.get("status") != "pass":
        blockers.append(f"{prefix}_artifact_not_pass")
    for key, blocker in _FALSE_ARTIFACT_FIELDS:
        if artifact.get(key) not in (False, None):
            blockers.append(f"{prefix}_artifact_{blocker}")
    return blockers


_EXPECTED_ARTIFACT_TYPES = {
    "selected_extract": "accurate_intake_websearch_selected_extract_packet_smoke_v1",
    "extract_result": "accurate_intake_websearch_extract_result_candidate_smoke_v1",
    "exact_review_packet": "accurate_intake_websearch_exact_candidate_review_packet_v1",
    "preflight": "accurate_intake_websearch_live_extract_preflight_v1",
}


_FALSE_ARTIFACT_FIELDS = (
    ("runtime_truth_changed", "changed_runtime_truth"),
    ("runtime_mutation_allowed", "allowed_runtime_mutation"),
    ("mutation_changed", "changed_mutation"),
    ("manager_context_changed", "changed_manager_context"),
    ("shared_contract_changed", "changed_shared_contract"),
    ("packetizer_format_changed", "changed_packetizer_format"),
    ("live_websearch_used", "used_live_websearch"),
    ("live_extract_used", "used_live_extract"),
    ("live_provider_used", "used_live_provider"),
    ("readiness_claimed", "claimed_readiness"),
)


def chain_blockers(
    selected: dict[str, Any],
    extract: dict[str, Any],
    review: dict[str, Any],
    preflight: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    selected_ids = _id_set(selected_packets(selected), "packet_id")
    extract_ids = _id_set(extract_candidates(extract), "candidate_id")
    review_ids = _id_set(review_packets(review), "packet_id")
    preflight_ids = _id_set(preflight_refs(preflight), "packet_id")
    if not selected_ids:
        blockers.append("selected_extract_packet_missing")
    if not extract_ids:
        blockers.append("extract_result_candidate_missing")
    if not review_ids:
        blockers.append("exact_review_packet_missing")
    blockers.extend(_missing_ref_blockers(extract, review, preflight))
    if selected_ids and _extract_selected_refs(extract) - selected_ids:
        blockers.append("extract_result_candidate_missing_selected_extract_source")
    if extract_ids and _review_extract_refs(review) - extract_ids:
        blockers.append("review_packet_missing_extract_result_source")
    if selected_ids and _review_selected_refs(review) - selected_ids:
        blockers.append("review_packet_missing_selected_extract_source")
    if preflight_ids and preflight_ids != review_ids:
        blockers.append("preflight_review_packet_ref_mismatch")
    if not preflight_ids:
        blockers.append("preflight_review_packet_ref_missing")
    blockers.extend(_truth_leak_blockers(selected, extract, review))
    return blockers


def _missing_ref_blockers(
    extract: dict[str, Any],
    review: dict[str, Any],
    preflight: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if _has_missing_ref(extract_candidates(extract), "source_selected_extract_packet_id"):
        blockers.append("extract_result_candidate_missing_selected_extract_source")
    if _has_missing_ref(review_packets(review), "source_extract_result_candidate_id"):
        blockers.append("review_packet_missing_extract_result_source")
    if _has_missing_ref(review_packets(review), "source_selected_extract_packet_id"):
        blockers.append("review_packet_missing_selected_extract_source")
    if _has_missing_ref(preflight_refs(preflight), "packet_id"):
        blockers.append("preflight_review_packet_ref_missing")
    return blockers


def _truth_leak_blockers(*artifacts: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for artifact in artifacts:
        for label, payloads in (
            ("selected_extract_packet", selected_packets(artifact)),
            ("extract_result_candidate", extract_candidates(artifact)),
            ("exact_review_packet", review_packets(artifact)),
        ):
            for payload in payloads:
                blockers.extend(_payload_truth_blockers(label, payload))
    return blockers


def _payload_truth_blockers(label: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key, blocker in _FALSE_PAYLOAD_FIELDS:
        if payload.get(key) is not False:
            blockers.append(f"{label}_{blocker}")
    return blockers


_FALSE_PAYLOAD_FIELDS = (
    ("runtime_truth_allowed", "allowed_runtime_truth"),
    ("promotion_allowed", "allowed_promotion"),
    ("exact_card_created", "created_exact_card"),
    ("runtime_mutation_allowed", "allowed_runtime_mutation"),
    ("raw_content_included", "included_raw_content"),
)


def payloads(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return selected_packets(artifact) + extract_candidates(artifact) + review_packets(artifact)


def selected_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in artifact.get("selected_extract_packets") or [] if isinstance(item, dict)]


def extract_candidates(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in artifact.get("extract_result_candidates") or [] if isinstance(item, dict)]


def review_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in artifact.get("review_packets") or [] if isinstance(item, dict)]


def preflight_refs(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in artifact.get("review_packet_refs") or [] if isinstance(item, dict)]


def chain_proof(
    selected: dict[str, Any],
    extract: dict[str, Any],
    review: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    return {
        "selected_extract_packet_ids": sorted(_id_set(selected_packets(selected), "packet_id")),
        "extract_result_candidate_ids": sorted(_id_set(extract_candidates(extract), "candidate_id")),
        "review_packet_ids": sorted(_id_set(review_packets(review), "packet_id")),
        "preflight_review_packet_ids": sorted(_id_set(preflight_refs(preflight), "packet_id")),
    }


def runtime_truth_count(*artifacts: dict[str, Any]) -> int:
    return sum(
        1
        for artifact in artifacts
        for payload in payloads(artifact)
        if payload.get("runtime_truth_allowed") is True
    )


def _id_set(items: list[dict[str, Any]], key: str) -> set[str]:
    return {str(item.get(key) or "") for item in items if str(item.get(key) or "").strip()}


def _has_missing_ref(items: list[dict[str, Any]], key: str) -> bool:
    return any(not str(item.get(key) or "").strip() for item in items)


def _extract_selected_refs(artifact: dict[str, Any]) -> set[str]:
    return _id_set(extract_candidates(artifact), "source_selected_extract_packet_id")


def _review_extract_refs(artifact: dict[str, Any]) -> set[str]:
    return _id_set(review_packets(artifact), "source_extract_result_candidate_id")


def _review_selected_refs(artifact: dict[str, Any]) -> set[str]:
    return _id_set(review_packets(artifact), "source_selected_extract_packet_id")
