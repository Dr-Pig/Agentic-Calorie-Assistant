from __future__ import annotations

import re
from typing import Any

from .exact_item_lookup import resolve_exact_item_fts


_KNOWN_BRANDS: list[str] = [
    "麥當勞",
    "McDonald's",
    "McDonald",
    "Starbucks",
    "星巴克",
    "Subway",
    "摩斯",
    "MOS",
    "松屋",
    "肯德基",
    "KFC",
    "必勝客",
    "Pizza Hut",
    "達美樂",
    "Domino",
    "全家",
    "7-ELEVEN",
    "7-11",
    "CITY CAFE",
    "CITY PRIMA",
    "Let's Cafe",
    "萊爾富",
    "HiLife",
    "OK",
    "義美",
    "光泉",
    "統一",
    "台酒",
    "金牌",
    "台灣啤酒",
    "麒麟",
    "Asahi",
    "Suntory",
    "泰山",
    "維他露",
    "舒跑",
    "FIN",
    "Power",
    "Monster",
    "紅牛",
    "MAISON",
    "HARIBO",
    "77",
    "Lotus",
    "新東陽",
    "黑橋牌",
    "新光三越",
    "的家",
    "家樂氏",
    "湖池屋",
    "阿春",
]


def _extract_brand(query: str) -> str | None:
    for brand in _KNOWN_BRANDS:
        if brand in query:
            return brand
    return None


def query_has_known_brand(query: str) -> bool:
    return _extract_brand(query) is not None


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


def resolve_chain_item(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """
    Fast retrieval for branded chain items.

    Strategy:
    1. Try FTS with original query (handles queries without spaces)
    2. If zero results, try FTS with spaces removed (handles "新東陽 蜜汁豬肉乾" issue)
    3. If brand+product query but brand alone is more specific, use brand-only query
    4. Merge results from multiple strategies, keeping BM25 order
    5. Apply brand-based re-ranking only to deprioritize wrong-brand results

    Returns results in a schema compatible with search_local_knowledge output.
    """
    if not query or not query.strip():
        return []

    original_query = query
    query_no_space = _normalize_spaces(query)
    brand_in_query = _extract_brand(query)
    brand_part, product_part = None, None

    if brand_in_query:
        idx = query.find(brand_in_query)
        before_brand = query[:idx].strip()
        after_brand = query[idx + len(brand_in_query):].strip()
        if before_brand:
            brand_part, product_part = before_brand, after_brand
        elif after_brand:
            brand_part, product_part = brand_in_query, after_brand
        else:
            brand_part = brand_in_query

    results_map: dict[tuple[str, str], dict[str, Any]] = {}
    for rank, item in enumerate(resolve_exact_item_fts(original_query, limit=limit * 2)):
        key = (str(item.get("title", "")), str(item.get("brand", "")))
        if key not in results_map:
            item["_found_by"] = "original"
            item["_bm25_rank"] = rank
            results_map[key] = item

    if query_no_space != original_query:
        for rank, item in enumerate(resolve_exact_item_fts(query_no_space, limit=limit * 2)):
            key = (str(item.get("title", "")), str(item.get("brand", "")))
            if key not in results_map:
                item["_found_by"] = "no_space"
                item["_bm25_rank"] = rank
                results_map[key] = item

    if brand_part and not any(v.get("_found_by") == "original" for v in results_map.values()):
        for rank, item in enumerate(resolve_exact_item_fts(brand_part, limit=limit * 2)):
            key = (str(item.get("title", "")), str(item.get("brand", "")))
            if key not in results_map:
                item["_found_by"] = "brand_only"
                item["_bm25_rank"] = rank
                results_map[key] = item

    if brand_in_query in ("CITY CAFE", "CITY PRIMA", "CITY PEARL") and results_map:
        first_key = next(iter(results_map.keys()))
        top_title = str(results_map[first_key].get("title", ""))
        if top_title.startswith("CITY ") and product_part:
            for rank, item in enumerate(resolve_exact_item_fts(product_part, limit=limit * 2)):
                key = (str(item.get("title", "")), str(item.get("brand", "")))
                if key not in results_map:
                    item["_found_by"] = "brand_stripped"
                    item["_bm25_rank"] = rank
                    results_map[key] = item

    if product_part:
        top_has_brand_prefix = False
        brand_only_dominated = False
        if results_map:
            top_title = str(list(results_map.values())[0].get("title", ""))
            top_has_brand_prefix = brand_in_query and top_title.startswith(brand_in_query)
            brand_only_dominated = all(
                v.get("_found_by") == "brand_only" for v in results_map.values()
            )
        if top_has_brand_prefix or brand_only_dominated or not results_map:
            product_results = resolve_exact_item_fts(product_part, limit=limit * 2)
            for rank, item in enumerate(product_results):
                key = (str(item.get("title", "")), str(item.get("brand", "")))
                if key not in results_map:
                    item["_found_by"] = "product_only"
                    item["_bm25_rank"] = rank
                    results_map[key] = item
            if not product_results and query_no_space:
                full_results = resolve_exact_item_fts(query_no_space, limit=limit * 2)
                for rank, item in enumerate(full_results):
                    key = (str(item.get("title", "")), str(item.get("brand", "")))
                    if key not in results_map:
                        item["_found_by"] = "full_query"
                        item["_bm25_rank"] = rank
                        results_map[key] = item

    if not results_map and original_query:
        tokens = original_query.split()
        for token in tokens:
            if len(token) >= 2:
                try:
                    prefix_q = token + "*"
                    prefix_results = resolve_exact_item_fts(prefix_q, limit=limit * 2)
                    for rank, item in enumerate(prefix_results):
                        key = (str(item.get("title", "")), str(item.get("brand", "")))
                        if key not in results_map:
                            item["_found_by"] = "token_prefix"
                            item["_bm25_rank"] = rank
                            results_map[key] = item
                except Exception:
                    pass  # FTS prefix syntax may not be supported for all queries

    if not results_map and brand_in_query and brand_part:
        try:
            brand_prefix_q = brand_part + "*"
            brand_prefix_results = resolve_exact_item_fts(brand_prefix_q, limit=limit * 2)
            for rank, item in enumerate(brand_prefix_results):
                key = (str(item.get("title", "")), str(item.get("brand", "")))
                if key not in results_map:
                    item["_found_by"] = "brand_prefix"
                    item["_bm25_rank"] = rank
                    results_map[key] = item
        except Exception:
            pass

    if brand_in_query and product_part and results_map:
        top_title = str(list(results_map.values())[0].get("title", ""))
        if not top_title.startswith(brand_in_query):
            and_query = f'"{brand_in_query}" AND "{product_part}"'
            and_results = resolve_exact_item_fts(and_query, limit=limit * 2)
            for rank, item in enumerate(and_results):
                key = (str(item.get("title", "")), str(item.get("brand", "")))
                if key not in results_map:
                    item["_found_by"] = "and_query"
                    item["_bm25_rank"] = rank
                    results_map[key] = item

    all_items = list(results_map.values())

    def _rerank_score(item: dict[str, Any]) -> tuple[int, int, int, int]:
        """
        Sort key: (tier, exact title match, exact brand match, BM25 rank).

        Tier 0 = exact title match (query_clean == title_clean)
        Tier 1 = original/no_space/brand_stripped source
        Tier 2 = brand_only source
        Tier 3 = all other fallback sources

        Within same tier: exact brand match first, then BM25 rank (lower = better).
        """
        found_by = item.get("_found_by", "")
        title = str(item.get("title") or "")
        q_clean = _normalize_spaces(original_query)
        t_clean = _normalize_spaces(title)

        if q_clean == t_clean:
            tier = 0
        elif found_by in ("original", "no_space", "brand_stripped", "full_query"):
            tier = 1
        elif found_by in ("brand_only", "product_only", "token_fallback", "token_prefix", "brand_prefix", "and_query"):
            tier = 2
        else:
            tier = 3

        item_brand = str(item.get("brand") or "")
        brand_exact_match = 0
        if brand_in_query and brand_in_query in item_brand:
            brand_exact_match = 1

        bm25_rank = item.get("_bm25_rank", 999)

        return (tier, -brand_exact_match, bm25_rank, 0)

    all_items.sort(key=_rerank_score)
    top_items = all_items[:limit]

    results: list[dict[str, Any]] = []
    for rank, item in enumerate(top_items, start=1):
        bm25_score = max(0, 100 - rank * 15)
        fts_confidence = str(item.get("match_confidence") or "medium")
        score = bm25_score + (24 if fts_confidence == "high" else 12)

        title = str(item.get("title") or "")
        q_clean = _normalize_spaces(original_query)
        t_clean = _normalize_spaces(title)

        if q_clean == t_clean:
            final_confidence = "high"
            match_path = "exact_title"
        elif fts_confidence == "high":
            final_confidence = "high"
            match_path = "brand_plus_alias_partial"
        else:
            final_confidence = fts_confidence
            match_path = "alias_partial"

        results.append(
            {
                "title": title,
                "brand": str(item.get("brand") or ""),
                "aliases": [],
                "category": str(item.get("category") or ""),
                "kcal": float(item.get("kcal") or 0),
                "kcal_band": str(item.get("kcal_band") or f"{item.get('kcal')} kcal"),
                "protein_g": float(item.get("protein_g") or 0),
                "carb_g": float(item.get("carb_g") or 0),
                "fat_g": float(item.get("fat_g") or 0),
                "serving_basis": str(item.get("serving_basis") or ""),
                "common_components": [],
                "portion_notes": str(item.get("portion_notes") or ""),
                "source_type": str(item.get("source_type") or "exact_item_card"),
                "source_url": item.get("source_url"),
                "confidence": final_confidence,
                "evidence_role": str(item.get("evidence_role") or "exact_truth"),
                "record_role": str(item.get("record_role") or "exact_item"),
                "match_confidence": final_confidence,
                "identity_confidence": final_confidence,
                "match_path": match_path,
                "source_class": "exact_item_db",
                "macro_completeness": str(item.get("macro_completeness") or "complete"),
                "estimate_eligibility": str(item.get("estimate_eligibility") or "exact"),
                "portion_basis_quality": str(item.get("portion_basis_quality") or "strong"),
                "score": score,
                "source": "exact_item_db",
                "kcal_low": _parse_kcal_low(item.get("kcal_band") or ""),
                "kcal_high": _parse_kcal_high(item.get("kcal_band") or ""),
                "kcal_most_likely": float(item.get("kcal") or 0),
                "must_ask_if_uncertain": [],
            }
        )

    return results


def _parse_kcal_low(kcal_band: str) -> float:
    if not kcal_band:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*\d+", kcal_band)
    if m:
        return float(m.group(1))
    m2 = re.search(r"^\D*([\d.]+)\s*kcal", kcal_band, re.IGNORECASE)
    if m2:
        return float(m2.group(1))
    return 0.0


def _parse_kcal_high(kcal_band: str) -> float:
    if not kcal_band:
        return 0.0
    m = re.search(r"\d+(?:\.\d+)?\s*-\s*(\d+(?:\.\d+)?)", kcal_band)
    if m:
        return float(m.group(1))
    m2 = re.search(r"^\D*([\d.]+)\s*kcal", kcal_band, re.IGNORECASE)
    if m2:
        return float(m2.group(1))
    return 0.0
