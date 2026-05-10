from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_offer_policy"
)


def offer_blockers(offer: Mapping[str, Any], allowed_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    candidate_id = str(offer.get("candidate_id", ""))
    if candidate_id not in allowed_ids:
        blockers.append(f"shadow_offer_packet_fixture.candidate_not_allowed:{candidate_id}")

    backup_ids = _string_list(offer.get("backup_candidate_ids"))
    blockers.extend(_backup_identity_blockers(candidate_id, backup_ids))
    for backup_id in backup_ids:
        if backup_id not in allowed_ids:
            blockers.append(
                f"shadow_offer_packet_fixture.backup_candidate_not_allowed:{backup_id}"
            )
    if offer.get("recommendation_served") is True:
        blockers.append("shadow_offer_packet_fixture.recommendation_served_not_allowed")
    if offer.get("is_canonical_truth") is True:
        blockers.append("shadow_offer_packet_fixture.is_canonical_truth_not_allowed")
    if offer.get("intake_commit_requested") is True:
        blockers.append("shadow_offer_packet_fixture.intake_commit_requested_not_allowed")
    return blockers


def _backup_identity_blockers(candidate_id: str, backup_ids: list[str]) -> list[str]:
    blockers: list[str] = []
    seen: set[str] = set()
    for backup_id in backup_ids:
        if backup_id == candidate_id:
            blockers.append(
                f"shadow_offer_packet_fixture.backup_matches_primary:{backup_id}"
            )
        if backup_id in seen:
            blockers.append(
                f"shadow_offer_packet_fixture.duplicate_backup_candidate_id:{backup_id}"
            )
        seen.add(backup_id)
    return list(dict.fromkeys(blockers))


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "offer_blockers"]
