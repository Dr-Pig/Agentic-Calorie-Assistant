from __future__ import annotations

from typing import Any

PACKET_MISMATCH_RISK_TYPES = (
    "wrong_item",
    "sibling_variant",
    "wrong_size",
    "wrong_modifier",
    "insufficient_evidence",
)

SAME_ITEM_MATCH_TYPES = {"exact", "alias_exact"}
EXACT_SOURCE_TYPES = {"exact_db", "web_search", "web_extract"}
EXACT_SOURCE_QUALITY = {"internal_exact", "official", "brand_menu"}


def sibling_variant_risk_present(packet: dict[str, Any]) -> bool:
    risk = packet.get("sibling_variant_risk")
    if isinstance(risk, dict):
        return bool(risk.get("present"))
    return bool(risk)


def exact_claim_mismatch_risks(packet: dict[str, Any]) -> tuple[str, ...]:
    risks: list[str] = []
    if sibling_variant_risk_present(packet):
        risks.append("sibling_variant")
    if packet.get("match_type") in {"related", "no_match"}:
        risks.append("wrong_item")
    if packet.get("size_or_serving_match") == "different":
        risks.append("wrong_size")
    if packet.get("modifier_match") == "different":
        risks.append("wrong_modifier")
    if not str(packet.get("serving_basis") or "").strip():
        risks.append("insufficient_evidence")
    return tuple(dict.fromkeys(risks))


def packet_supports_exact_claim(packet: dict[str, Any]) -> bool:
    return (
        packet.get("source_type") in EXACT_SOURCE_TYPES
        and packet.get("source_quality_label") in EXACT_SOURCE_QUALITY
        and packet.get("match_type") in SAME_ITEM_MATCH_TYPES
        and not exact_claim_mismatch_risks(packet)
    )
