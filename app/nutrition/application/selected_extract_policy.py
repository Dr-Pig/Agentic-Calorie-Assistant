from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Sequence

from .websearch_selected_extract_ranking import choose_highest_priority_extract_packet
from .websearch_source_policy import classify_websearch_source_candidate


@dataclass(frozen=True)
class SelectedExtractDecision:
    selected_search_packet_id: str | None
    selected_urls: list[str]
    extract_reason: str | None
    extract_allowed_by_policy: bool
    max_extract_urls: int
    extract_count: int
    source_policy_block_reasons: list[str] = field(default_factory=list)

    def to_trace(self) -> dict[str, object]:
        trace: dict[str, object] = {
            "selected_search_packet_id": self.selected_search_packet_id,
            "extract_reason": self.extract_reason,
            "extract_allowed_by_policy": self.extract_allowed_by_policy,
            "max_extract_urls": self.max_extract_urls,
            "extract_count": self.extract_count,
        }
        if self.source_policy_block_reasons:
            trace["source_policy_block_reasons"] = list(self.source_policy_block_reasons)
        return trace


def choose_selected_extract_packet(
    packets: Sequence[dict[str, object]],
) -> SelectedExtractDecision:
    max_extract_urls = 1
    eligible_packets: list[dict[str, object]] = []
    source_policy_block_reasons: list[str] = []
    for packet in packets:
        if not _has_identity_safe_extract_shape(packet):
            continue
        source_policy = _source_policy_for_packet(packet)
        if source_policy["extract_candidate_allowed"] is not True:
            source_policy_block_reasons.extend(
                str(reason)
                for reason in source_policy.get("block_reasons", [])
                if str(reason).strip()
            )
            continue
        eligible_packets.append(packet)

    selected_packet = choose_highest_priority_extract_packet(eligible_packets)
    if selected_packet is not None:
        url = str(selected_packet.get("url") or "").strip()
        if url:
            return SelectedExtractDecision(
                selected_search_packet_id=str(selected_packet.get("packet_id") or "").strip()
                or None,
                selected_urls=[url],
                extract_reason="selected_same_item_official_candidate",
                extract_allowed_by_policy=True,
                max_extract_urls=max_extract_urls,
                extract_count=1,
            )

    if source_policy_block_reasons:
        return SelectedExtractDecision(
            selected_search_packet_id=None,
            selected_urls=[],
            extract_reason="source_policy_blocked_selected_extract",
            extract_allowed_by_policy=False,
            max_extract_urls=max_extract_urls,
            extract_count=0,
            source_policy_block_reasons=sorted(set(source_policy_block_reasons)),
        )

    return SelectedExtractDecision(
        selected_search_packet_id=None,
        selected_urls=[],
        extract_reason="no_exact_same_item_search_packet",
        extract_allowed_by_policy=False,
        max_extract_urls=max_extract_urls,
        extract_count=0,
    )


def _has_identity_safe_extract_shape(packet: dict[str, object]) -> bool:
    modifier_match = str(packet.get("modifier_match") or "").strip()
    identity_safe = (
        str(packet.get("match_type") or "").strip() == "exact"
        and not bool((packet.get("sibling_variant_risk") or {}).get("present"))
        and str(packet.get("size_or_serving_match") or "").strip() != "different"
        and modifier_match not in {"different", "unknown"}
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


def _source_policy_for_packet(packet: dict[str, object]) -> dict[str, object]:
    return classify_websearch_source_candidate(
        {
            "source_url": packet.get("url"),
            "source_class": _source_class_from_packet(packet),
            "license_status": packet.get("license_status"),
            "robots_status": packet.get("robots_status"),
            "identity_confidence": packet.get("identity_confidence"),
            "serving_basis_candidate": packet.get("serving_basis_candidate")
            or packet.get("serving_basis"),
            "nutrition_fields_present": packet.get("nutrition_fields_present"),
        }
    )


def _source_class_from_packet(packet: dict[str, object]) -> str:
    explicit_source_class = str(packet.get("source_class_hint") or "").strip().lower()
    if explicit_source_class:
        return explicit_source_class
    source_quality = str(packet.get("source_quality_label") or "").strip().lower()
    officialness = str(packet.get("officialness_hint") or "").strip().lower()
    if source_quality == "third_party" or officialness == "unknown":
        return "third_party_blog_or_scrape"
    if officialness == "official" or source_quality in {"official", "brand_menu"}:
        return "official_brand_or_chain_page"
    return "high_quality_search_candidate"


__all__ = ["SelectedExtractDecision", "choose_selected_extract_packet"]
