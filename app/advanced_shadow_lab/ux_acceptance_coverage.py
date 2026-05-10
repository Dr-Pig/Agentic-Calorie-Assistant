from __future__ import annotations

from typing import Any, Mapping


REQUIRED_UX_JOURNEY_IDS = ["F", "F2", "I", "L", "M", "N"]
UX_ACCEPTANCE_ROLE = "acceptance_map_not_product_readiness_authority"
ADVANCED_CAPABILITY_GAP_REVIEW_SLICE = "advanced_capability_gap_review"
REQUIRED_UX_LIST_FIELDS = (
    "capability_domains",
    "product_contract_refs",
    "existing_shadow_artifacts",
    "required_trace_fields",
)
ALLOWED_UX_ACCEPTANCE_STATUSES = {
    "existing_shadow_chain_mapped",
    "gap_requires_next_slice",
}


def build_ux_acceptance_summary(
    contract: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    mapped_count = _count_status(entries, "existing_shadow_chain_mapped")
    gap_count = _count_status(entries, "gap_requires_next_slice")
    stale_next_slices = stale_next_slice_journey_ids(entries)
    return {
        "required_journey_ids": list(REQUIRED_UX_JOURNEY_IDS),
        "mapped_journey_count": len(entries),
        "missing_journey_ids": missing_ux_journeys(entries),
        "existing_shadow_chain_mapped_count": mapped_count,
        "gap_requires_next_slice_count": gap_count,
        "stale_next_slice_journey_ids": stale_next_slices,
        "closure_next_build_slice": ADVANCED_CAPABILITY_GAP_REVIEW_SLICE,
        "mapped_chain_closure_status": _closure_status(
            missing_ux_journeys(entries),
            gap_count,
            stale_next_slices,
        ),
        "new_report_family_created": contract.get("new_report_family_created") is True,
        "mainline_activation_allowed": any(
            entry.get("mainline_activation_allowed") is True for entry in entries
        ),
    }


def ux_acceptance_blockers(
    contract: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if contract.get("ux_acceptance_role") != UX_ACCEPTANCE_ROLE:
        blockers.append("ux_acceptance_role_not_non_readiness_authority")
    missing = missing_ux_journeys(entries)
    if missing:
        blockers.append(f"ux_acceptance_missing_journeys:{','.join(missing)}")
    for entry in entries:
        blockers.extend(_entry_blockers(entry))
    return blockers


def missing_ux_journeys(entries: list[Mapping[str, Any]]) -> list[str]:
    journey_ids = {str(entry.get("journey_id") or "") for entry in entries}
    return [
        journey_id
        for journey_id in REQUIRED_UX_JOURNEY_IDS
        if journey_id not in journey_ids
    ]


def stale_next_slice_journey_ids(entries: list[Mapping[str, Any]]) -> list[str]:
    return [
        str(entry.get("journey_id") or "unknown_journey")
        for entry in entries
        if str(entry.get("next_build_slice") or "").strip()
        != ADVANCED_CAPABILITY_GAP_REVIEW_SLICE
    ]


def _entry_blockers(entry: Mapping[str, Any]) -> list[str]:
    journey_id = str(entry.get("journey_id") or "unknown_journey")
    prefix = f"ux_acceptance[{journey_id}]"
    status = str(entry.get("acceptance_status") or "")
    next_build_slice = str(entry.get("next_build_slice") or "").strip()
    blockers: list[str] = []
    if journey_id not in REQUIRED_UX_JOURNEY_IDS:
        blockers.append(f"{prefix}.unsupported_journey_id")
    blockers.extend(_required_list_field_blockers(prefix, entry))
    blockers.extend(_next_slice_blockers(prefix, next_build_slice))
    blockers.extend(_claim_boundary_blockers(prefix, entry))
    blockers.extend(_status_blockers(prefix, status))
    return blockers


def _required_list_field_blockers(
    prefix: str,
    entry: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for field in REQUIRED_UX_LIST_FIELDS:
        if not entry.get(field):
            blockers.append(f"{prefix}.{field}_missing")
    return blockers


def _next_slice_blockers(prefix: str, next_build_slice: str) -> list[str]:
    if not next_build_slice:
        return [f"{prefix}.next_build_slice_missing"]
    if next_build_slice != ADVANCED_CAPABILITY_GAP_REVIEW_SLICE:
        return [f"{prefix}.stale_next_build_slice:{next_build_slice}"]
    return []


def _claim_boundary_blockers(
    prefix: str,
    entry: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if entry.get("claim_boundary") != "non_claim":
        blockers.append(f"{prefix}.claim_boundary_not_non_claim")
    if entry.get("mainline_activation_allowed") is not False:
        blockers.append(f"{prefix}.mainline_activation_allowed")
    return blockers


def _status_blockers(prefix: str, status: str) -> list[str]:
    blockers: list[str] = []
    if status not in ALLOWED_UX_ACCEPTANCE_STATUSES:
        blockers.append(f"{prefix}.unsupported_acceptance_status")
    if status == "gap_requires_next_slice":
        blockers.append(f"{prefix}.gap_requires_next_slice_not_closed")
    return blockers


def _count_status(entries: list[Mapping[str, Any]], status: str) -> int:
    return sum(1 for entry in entries if entry.get("acceptance_status") == status)


def _closure_status(
    missing: list[str],
    gap_count: int,
    stale_next_slices: list[str],
) -> str:
    if missing:
        return "missing_required_journeys"
    if gap_count:
        return "open_gap_requires_next_slice"
    if stale_next_slices:
        return "stale_next_build_slice"
    return "closed_for_gap_review"


__all__ = [
    "ADVANCED_CAPABILITY_GAP_REVIEW_SLICE",
    "REQUIRED_UX_JOURNEY_IDS",
    "UX_ACCEPTANCE_ROLE",
    "build_ux_acceptance_summary",
    "missing_ux_journeys",
    "stale_next_slice_journey_ids",
    "ux_acceptance_blockers",
]
