from __future__ import annotations

from typing import Any


def source_class_from_packet(packet: dict[str, Any]) -> str:
    explicit_source_class = str(packet.get("source_class_hint") or "").strip().lower()
    if explicit_source_class:
        return explicit_source_class
    source_quality = str(packet.get("source_quality_label") or "")
    officialness = str(packet.get("officialness_hint") or "")
    if source_quality == "third_party" or officialness == "unknown":
        return "third_party_blog_or_scrape"
    if officialness == "official":
        return "official_brand_or_chain_page"
    return "high_quality_search_candidate"


__all__ = ["source_class_from_packet"]
