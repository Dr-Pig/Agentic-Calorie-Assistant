from __future__ import annotations

from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .fooddb_retrieval_policy import IndexedFoodRecord
from .retrieval_intent import RetrievalIntent


def records_for_query(
    *,
    index: FoodEvidenceIndexPort,
    query: str,
) -> tuple[IndexedFoodRecord, ...]:
    search_records = getattr(index, "search_records", None)
    if callable(search_records):
        records = search_records(query, limit=20)
        if records:
            return records
    return index.load_records()


def query_from_intent(intent: RetrievalIntent) -> str:
    parts = [
        *(str(alias).strip() for alias in intent.aliases if str(alias).strip()),
        str(intent.base_dish or "").strip(),
    ]
    for part in parts:
        if part:
            return part
    return ""


def websearch_packets_for_intent(
    intent: RetrievalIntent,
    *,
    packet_smoke: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    brand = str(intent.brand_hint or "").strip().lower()
    identity_terms = {
        str(intent.base_dish or "").strip().lower(),
        *(str(alias).strip().lower() for alias in intent.aliases if str(alias).strip()),
    }
    scoped_packets = []
    for item in packet_smoke.get("cases") or []:
        packet = item.get("websearch_candidate_packet") if isinstance(item, dict) else None
        if not isinstance(packet, dict):
            continue
        title = str(packet.get("title") or "").lower()
        query = str(packet.get("query") or "").lower()
        brand_matches = not brand or brand in title or brand in query
        identity_matches = any(term and (term in title or term in query) for term in identity_terms)
        exact_enough = (
            packet.get("match_type") == "exact"
            and packet.get("brand_match") in {"exact", "same"}
            and packet.get("source_quality_label") in {"brand_menu", "official_brand"}
        )
        if brand_matches and identity_matches and exact_enough:
            scoped_packets.append(packet)
    return tuple(scoped_packets)


__all__ = [
    "query_from_intent",
    "records_for_query",
    "websearch_packets_for_intent",
]
