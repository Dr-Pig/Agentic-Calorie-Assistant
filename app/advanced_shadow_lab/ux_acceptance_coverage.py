from __future__ import annotations

from typing import Any, Mapping


REQUIRED_UX_JOURNEY_IDS = ["F", "F2", "I", "L", "M", "N"]
UX_ACCEPTANCE_ROLE = "acceptance_map_not_product_readiness_authority"
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
    return {
        "required_journey_ids": list(REQUIRED_UX_JOURNEY_IDS),
        "mapped_journey_count": len(entries),
        "missing_journey_ids": missing_ux_journeys(entries),
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


def _entry_blockers(entry: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    journey_id = str(entry.get("journey_id") or "unknown_journey")
    prefix = f"ux_acceptance[{journey_id}]"
    if journey_id not in REQUIRED_UX_JOURNEY_IDS:
        blockers.append(f"{prefix}.unsupported_journey_id")
    for field in REQUIRED_UX_LIST_FIELDS:
        if not entry.get(field):
            blockers.append(f"{prefix}.{field}_missing")
    if not str(entry.get("next_build_slice") or "").strip():
        blockers.append(f"{prefix}.next_build_slice_missing")
    if entry.get("claim_boundary") != "non_claim":
        blockers.append(f"{prefix}.claim_boundary_not_non_claim")
    if entry.get("mainline_activation_allowed") is not False:
        blockers.append(f"{prefix}.mainline_activation_allowed")
    if entry.get("acceptance_status") not in ALLOWED_UX_ACCEPTANCE_STATUSES:
        blockers.append(f"{prefix}.unsupported_acceptance_status")
    return blockers


__all__ = [
    "REQUIRED_UX_JOURNEY_IDS",
    "UX_ACCEPTANCE_ROLE",
    "build_ux_acceptance_summary",
    "missing_ux_journeys",
    "ux_acceptance_blockers",
]
