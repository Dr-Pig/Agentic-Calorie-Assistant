from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


_SOURCE_CLASS_PRIORITY = {
    "official_nutrition_pdf": 3,
    "brand_menu_page": 2,
    "official_brand_or_chain_page": 1,
}
_SOURCE_QUALITY_PRIORITY = {
    "brand_menu": 2,
    "official": 1,
}
_MATCH_PRIORITY = {
    "same": 2,
    "not_applicable": 1,
}


@dataclass(frozen=True)
class RankedSelectedExtractPacket:
    packet: dict[str, object]
    score: tuple[int, int, int, int, float, str]


def choose_highest_priority_extract_packet(
    packets: Sequence[dict[str, object]],
) -> dict[str, object] | None:
    ranked = ranked_extract_packets(packets)
    if not ranked:
        return None
    return ranked[0].packet


def ranked_extract_packets(
    packets: Sequence[dict[str, object]],
) -> tuple[RankedSelectedExtractPacket, ...]:
    ranked = [
        RankedSelectedExtractPacket(packet=packet, score=_packet_score(packet))
        for packet in packets
    ]
    return tuple(sorted(ranked, key=lambda item: item.score, reverse=True))


def _packet_score(packet: dict[str, object]) -> tuple[int, int, int, int, float, str]:
    return (
        _source_class_score(packet),
        _source_quality_score(packet),
        _match_score(packet, key="modifier_match"),
        _match_score(packet, key="size_or_serving_match"),
        _numeric_score(packet.get("tavily_score")),
        str(packet.get("packet_id") or ""),
    )


def _source_class_score(packet: dict[str, object]) -> int:
    source_class = str(packet.get("source_class_hint") or "").strip().lower()
    return _SOURCE_CLASS_PRIORITY.get(source_class, 0)


def _source_quality_score(packet: dict[str, object]) -> int:
    source_quality = str(packet.get("source_quality_label") or "").strip().lower()
    return _SOURCE_QUALITY_PRIORITY.get(source_quality, 0)


def _match_score(packet: dict[str, object], *, key: str) -> int:
    value = str(packet.get(key) or "").strip().lower()
    return _MATCH_PRIORITY.get(value, 0)


def _numeric_score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


__all__ = [
    "RankedSelectedExtractPacket",
    "choose_highest_priority_extract_packet",
    "ranked_extract_packets",
]
