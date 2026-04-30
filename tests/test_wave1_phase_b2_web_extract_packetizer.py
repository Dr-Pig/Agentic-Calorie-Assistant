from __future__ import annotations

from app.nutrition.application.evidence_candidate_packetizer import add_hard_recheck_metadata
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets
from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.application.web_extract_packetizer import build_web_extract_packets


def _intent() -> RetrievalIntent:
    return RetrievalIntent(
        base_dish="珍珠紅茶拿鐵",
        aliases=["迷客夏珍珠紅茶拿鐵"],
        brand_hint="迷客夏",
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _selected_packet() -> dict[str, object]:
    return {
        "packet_id": "pkt_web_search_milksha_exact",
        "packet_type": "SearchCandidatePacket",
        "truth_level": "candidate",
        "source_type": "web_search",
        "source_quality_label": "brand_menu",
        "raw_ref": "raw/tavily/search.json#0",
        "title": "迷客夏 珍珠紅茶拿鐵",
        "url": "https://milksha.example/menu/pearl-black-tea-latte",
        "snippet": "official menu result",
        "tavily_score": 0.93,
        "query": "迷客夏珍珠紅茶拿鐵",
        "matched_terms": ["迷客夏", "珍珠紅茶拿鐵"],
        "matched_name": "迷客夏珍珠紅茶拿鐵",
        "canonical_name": "迷客夏 珍珠紅茶拿鐵",
        "match_type": "exact",
        "brand_match": "same",
        "size_or_serving_match": "same",
        "modifier_match": "same",
        "serving_basis": "per_cup",
        "sibling_variant_risk": {"present": False, "reason": None},
        "supports_exact_claim": True,
        "hard_recheck_risks": [],
    }


def test_web_extract_packetizer_builds_exact_support_packet_with_kcal_and_known_serving_basis() -> None:
    packets = build_web_extract_packets(
        _intent(),
        selected_search_packet=_selected_packet(),
        extract_rows=[
            {
                "url": "https://milksha.example/menu/pearl-black-tea-latte",
                "title": "迷客夏 珍珠紅茶拿鐵",
                "officialness": "official",
                "source_type": "official",
                "serving_basis": "per_cup",
                "brand_detected": "milksha",
                "raw_content": "每杯 400 kcal",
            }
        ],
    )

    assert len(packets) == 1
    packet = packets[0]
    assert packet["packet_id"].startswith("pkt_web_extract_")
    assert packet["packet_type"] == "WebExtractCandidatePacket"
    assert packet["truth_level"] == "candidate"
    assert packet["source_type"] == "web_extract"
    assert packet["source_quality_label"] == "brand_menu"
    assert packet["selected_search_packet_id"] == "pkt_web_search_milksha_exact"
    assert packet["match_type"] == "exact"
    assert packet["brand_match"] == "same"
    assert packet["serving_basis"] == "per_cup"
    assert packet["kcal"] == 400.0


def test_web_extract_packetizer_rejects_ambiguous_kcal_values() -> None:
    packets = build_web_extract_packets(
        _intent(),
        selected_search_packet=_selected_packet(),
        extract_rows=[
            {
                "url": "https://milksha.example/menu/pearl-black-tea-latte",
                "title": "迷客夏 珍珠紅茶拿鐵",
                "officialness": "official",
                "source_type": "official",
                "serving_basis": "per_cup",
                "brand_detected": "milksha",
                "raw_content": "每杯 400 kcal，第二欄顯示 520 kcal",
            }
        ],
    )

    assert packets == ()


def test_web_extract_packetizer_rejects_unknown_serving_basis() -> None:
    packets = build_web_extract_packets(
        _intent(),
        selected_search_packet=_selected_packet(),
        extract_rows=[
            {
                "url": "https://milksha.example/menu/pearl-black-tea-latte",
                "title": "迷客夏 珍珠紅茶拿鐵",
                "officialness": "official",
                "source_type": "official",
                "serving_basis": "unknown",
                "brand_detected": "milksha",
                "raw_content": "400 kcal",
            }
        ],
    )

    assert packets == ()


def test_packet_consumption_accepts_web_extract_exact_support_only_as_exact_evidence() -> None:
    packet = add_hard_recheck_metadata(
        build_web_extract_packets(
            _intent(),
            selected_search_packet=_selected_packet(),
            extract_rows=[
                {
                    "url": "https://milksha.example/menu/pearl-black-tea-latte",
                    "title": "迷客夏 珍珠紅茶拿鐵",
                    "officialness": "official",
                    "source_type": "official",
                    "serving_basis": "per_cup",
                    "brand_detected": "milksha",
                    "raw_content": "每杯 400 kcal",
                }
            ],
        )[0]
    )

    result = consume_rechecked_packets((packet,))

    assert result.rejected_candidates == ()
    assert len(result.accepted_packets) == 1
    assert result.accepted_packets[0]["accepted_usage"] == "exact"
