from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class EvidencePacketConsumptionResult:
    accepted_packets: tuple[dict[str, object], ...]
    rejected_candidates: tuple[dict[str, object], ...]
    consumed_packet_ids: tuple[str, ...]


def consume_rechecked_packets(packets: Sequence[dict[str, object]]) -> EvidencePacketConsumptionResult:
    accepted_packets: list[dict[str, object]] = []
    rejected_candidates: list[dict[str, object]] = []
    consumed_packet_ids: list[str] = []

    for packet in packets:
        packet_id = str(packet.get("packet_id") or "").strip()
        if packet_id:
            consumed_packet_ids.append(packet_id)

        source_type = str(packet.get("source_type") or "").strip()
        if source_type == "generic_db":
            accepted = dict(packet)
            accepted["accepted_usage"] = "anchor"
            accepted_packets.append(accepted)
            continue

        if source_type in {"exact_db", "web_search", "web_extract"}:
            hard_recheck_risks = tuple(
                str(risk).strip() for risk in packet.get("hard_recheck_risks", []) if str(risk).strip()
            )
            if packet.get("supports_exact_claim") is True and not hard_recheck_risks:
                accepted = dict(packet)
                accepted["accepted_usage"] = "exact"
                accepted_packets.append(accepted)
                continue
            rejected_candidates.append(_build_rejected_candidate(packet, hard_recheck_risks))
            continue

        rejected_candidates.append(_build_rejected_candidate(packet, ("insufficient_evidence",)))

    return EvidencePacketConsumptionResult(
        accepted_packets=tuple(accepted_packets),
        rejected_candidates=tuple(rejected_candidates),
        consumed_packet_ids=tuple(consumed_packet_ids),
    )


def _build_rejected_candidate(
    packet: dict[str, object],
    hard_recheck_risks: tuple[str, ...],
) -> dict[str, object]:
    risk_type = hard_recheck_risks[0] if hard_recheck_risks else "insufficient_evidence"
    if hard_recheck_risks:
        reason = f"deterministic_hard_recheck_failed:{','.join(hard_recheck_risks)}"
    else:
        reason = "exact_claim_not_supported_by_deterministic_recheck"
    return {
        "packet_id": packet.get("packet_id"),
        "risk_type": risk_type,
        "reason": reason,
        "canonical_name": packet.get("canonical_name"),
        "source_type": packet.get("source_type"),
        "usable_as_evidence": False,
        "exact_claim_blocked": True,
        "estimability_blocked": False,
    }


__all__ = ["EvidencePacketConsumptionResult", "consume_rechecked_packets"]
