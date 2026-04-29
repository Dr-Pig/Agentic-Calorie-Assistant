from __future__ import annotations

import hashlib
import re
from typing import Mapping, Sequence

from .context_normalizer import lookup_key, normalize_text
from .retrieval_intent import RetrievalIntent

_KCAL_FIELD_KEYS = ("kcal", "label_kcal", "kcal_band")
_EXPLICIT_KCAL_PATTERNS = (
    re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:kcal|calories?)\b", re.IGNORECASE),
    re.compile(r"熱量[:：]?\s*(\d+(?:\.\d+)?)\s*(?:大卡|卡|kcal)?", re.IGNORECASE),
)


def build_web_extract_packets(
    intent: RetrievalIntent,
    *,
    selected_search_packet: dict[str, object],
    extract_rows: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    packets: list[dict[str, object]] = []
    selected_url = _text(selected_search_packet.get("url"))
    for row in extract_rows:
        if _text(row.get("url")) != selected_url:
            continue
        packet = _build_web_extract_packet(intent, selected_search_packet=selected_search_packet, row=row)
        if packet is not None:
            packets.append(packet)
    return tuple(packets)


def _build_web_extract_packet(
    intent: RetrievalIntent,
    *,
    selected_search_packet: dict[str, object],
    row: Mapping[str, object],
) -> dict[str, object] | None:
    serving_basis = _serving_basis(row.get("serving_basis"))
    if serving_basis is None:
        return None

    kcal = _extract_exact_kcal(row)
    if kcal is None:
        return None

    title = _text(row.get("title")) or _text(selected_search_packet.get("title"))
    requested_name = _requested_identity(intent, selected_search_packet)
    if lookup_key(title) != lookup_key(_text(selected_search_packet.get("canonical_name"))):
        return None
    if lookup_key(requested_name) and lookup_key(requested_name) != lookup_key(_text(selected_search_packet.get("matched_name"))):
        return None

    raw_ref = _text(row.get("raw_ref")) or _default_raw_ref(
        selected_search_packet_id=_text(selected_search_packet.get("packet_id")),
        url=_text(row.get("url")),
        title=title,
    )
    packet_id = _default_packet_id(selected_search_packet_id=_text(selected_search_packet.get("packet_id")), raw_ref=raw_ref)
    kcal_band = _kcal_band(row, kcal=kcal)

    packet: dict[str, object] = {
        "packet_id": packet_id,
        "packet_type": "WebExtractCandidatePacket",
        "truth_level": "candidate",
        "source_type": "web_extract",
        "source_quality_label": _text(selected_search_packet.get("source_quality_label")) or "official",
        "raw_ref": raw_ref,
        "title": title,
        "url": _text(row.get("url")),
        "matched_name": requested_name,
        "canonical_name": title,
        "match_type": "exact",
        "brand_match": _text(selected_search_packet.get("brand_match")) or "same",
        "size_or_serving_match": "same",
        "modifier_match": "unknown",
        "serving_basis": serving_basis,
        "sibling_variant_risk": {"present": False, "reason": None},
        "kcal": kcal,
        "selected_search_packet_id": _text(selected_search_packet.get("packet_id")),
    }
    if kcal_band is not None:
        packet["kcal_band"] = kcal_band
    return packet


def _extract_exact_kcal(row: Mapping[str, object]) -> float | None:
    field_values = [_parse_single_kcal_value(row.get(key)) for key in _KCAL_FIELD_KEYS]
    parsed_field_values = [value for value in field_values if value is not None]
    if len(set(parsed_field_values)) > 1:
        return None
    if len(parsed_field_values) == 1:
        return parsed_field_values[0]

    raw_content = _text(row.get("raw_content"))
    matches: list[float] = []
    for pattern in _EXPLICIT_KCAL_PATTERNS:
        for matched in pattern.findall(raw_content):
            try:
                matches.append(float(matched))
            except ValueError:
                continue
    deduped = list(dict.fromkeys(matches))
    if len(deduped) != 1:
        return None
    return deduped[0]


def _parse_single_kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value)
    if not text:
        return None
    matches: list[float] = []
    for pattern in _EXPLICIT_KCAL_PATTERNS:
        for matched in pattern.findall(text):
            try:
                matches.append(float(matched))
            except ValueError:
                continue
    deduped = list(dict.fromkeys(matches))
    if len(deduped) != 1:
        return None
    return deduped[0]


def _serving_basis(value: object) -> str | None:
    serving_basis = _text(value)
    if not serving_basis or serving_basis == "unknown":
        return None
    return serving_basis


def _kcal_band(row: Mapping[str, object], *, kcal: float) -> str | None:
    raw_band = _text(row.get("kcal_band"))
    if raw_band:
        return raw_band
    if kcal.is_integer():
        return f"{int(kcal)} kcal"
    return f"{kcal} kcal"


def _requested_identity(intent: RetrievalIntent, selected_search_packet: Mapping[str, object]) -> str:
    for alias in intent.aliases:
        alias_text = _text(alias)
        if alias_text:
            return alias_text
    if intent.base_dish:
        return _text(intent.base_dish)
    return _text(selected_search_packet.get("matched_name")) or _text(selected_search_packet.get("canonical_name"))


def _default_raw_ref(*, selected_search_packet_id: str, url: str, title: str) -> str:
    digest = hashlib.sha1(f"{selected_search_packet_id}|{url}|{title}".encode("utf-8")).hexdigest()[:10]
    return f"web_extract_row:{digest}"


def _default_packet_id(*, selected_search_packet_id: str, raw_ref: str) -> str:
    digest = hashlib.sha1(f"{selected_search_packet_id}|{raw_ref}".encode("utf-8")).hexdigest()[:12]
    return f"pkt_web_extract_{digest}"


def _text(value: object) -> str:
    return normalize_text(value) if isinstance(value, str) else ""


__all__ = ["build_web_extract_packets"]
