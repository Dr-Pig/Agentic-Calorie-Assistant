from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SelectedExtractDecision:
    selected_search_packet_id: str | None
    selected_urls: list[str]
    extract_reason: str | None
    extract_allowed_by_policy: bool
    max_extract_urls: int
    extract_count: int

    def to_trace(self) -> dict[str, object]:
        return {
            "selected_search_packet_id": self.selected_search_packet_id,
            "extract_reason": self.extract_reason,
            "extract_allowed_by_policy": self.extract_allowed_by_policy,
            "max_extract_urls": self.max_extract_urls,
            "extract_count": self.extract_count,
        }


def choose_selected_extract_packet(
    packets: Sequence[dict[str, object]],
) -> SelectedExtractDecision:
    max_extract_urls = 1
    for packet in packets:
        if not _qualifies_for_selected_extract(packet):
            continue
        url = str(packet.get("url") or "").strip()
        if not url:
            continue
        return SelectedExtractDecision(
            selected_search_packet_id=str(packet.get("packet_id") or "").strip() or None,
            selected_urls=[url],
            extract_reason="selected_same_item_official_candidate",
            extract_allowed_by_policy=True,
            max_extract_urls=max_extract_urls,
            extract_count=1,
        )

    return SelectedExtractDecision(
        selected_search_packet_id=None,
        selected_urls=[],
        extract_reason="no_exact_same_item_search_packet",
        extract_allowed_by_policy=False,
        max_extract_urls=max_extract_urls,
        extract_count=0,
    )


def _qualifies_for_selected_extract(packet: dict[str, object]) -> bool:
    identity_safe = (
        str(packet.get("match_type") or "").strip() == "exact"
        and not bool((packet.get("sibling_variant_risk") or {}).get("present"))
        and str(packet.get("size_or_serving_match") or "").strip() != "different"
        and str(packet.get("modifier_match") or "").strip() != "different"
        and not tuple(
            risk
            for risk in (str(risk).strip() for risk in packet.get("hard_recheck_risks", []) if str(risk).strip())
            if risk != "insufficient_evidence"
        )
    )
    return (
        str(packet.get("source_type") or "").strip() == "web_search"
        and str(packet.get("source_quality_label") or "").strip() in {"official", "brand_menu"}
        and identity_safe
    )


__all__ = ["SelectedExtractDecision", "choose_selected_extract_packet"]
