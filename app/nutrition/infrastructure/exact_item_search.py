from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import text

from .exact_item_card_loader import load_exact_item_card_seed_records


@lru_cache(maxsize=1)
def _load_cards() -> list[dict[str, Any]]:
    return list(load_exact_item_card_seed_records())


@lru_cache(maxsize=1)
def _cards_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(card.get("card_id") or card.get("id") or card.get("item_id") or ""): card
        for card in _load_cards()
        if str(card.get("card_id") or card.get("id") or card.get("item_id") or "")
    }


def ensure_exact_item_fts() -> None:
    from app.database import engine

    cards = _load_cards()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS exact_item_search
                USING fts5(
                    item_id UNINDEXED,
                    title,
                    aliases,
                    brand,
                    tokenize='unicode61'
                )
                """
            )
        )
        existing = conn.execute(text("SELECT count(*) FROM exact_item_search")).scalar() or 0
        if int(existing) > 0:
            return
        for card in cards:
            aliases = " ".join(str(item).strip() for item in card.get("aliases", []) if str(item).strip())
            item_id = str(card.get("card_id") or card.get("id") or card.get("item_id") or "")
            conn.execute(
                text(
                    """
                    INSERT INTO exact_item_search(item_id, title, aliases, brand)
                    VALUES (:item_id, :title, :aliases, :brand)
                    """
                ),
                {
                    "item_id": item_id,
                    "title": str(card.get("title") or ""),
                    "aliases": aliases,
                    "brand": str(card.get("brand") or ""),
                },
            )


def resolve_exact_item_fts(query: str, *, limit: int = 3) -> list[dict[str, Any]]:
    from app.database import engine

    ensure_exact_item_fts()
    query = str(query or "").strip()
    if not query:
        return []
    by_id = _cards_by_id()
    escaped_terms = [term.replace('"', " ").strip() for term in query.split() if term.strip()]
    if len(escaped_terms) == 1 and escaped_terms[0].endswith("*"):
        match_query = escaped_terms[0]
    elif any(term.endswith("*") for term in escaped_terms):
        match_query = " AND ".join(f'"{term}"' for term in escaped_terms)
    else:
        match_query = " OR ".join(f'"{term}"' for term in escaped_terms) or query
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT item_id, title, brand, bm25(exact_item_search) AS rank
                FROM exact_item_search
                WHERE exact_item_search MATCH :match_query
                ORDER BY rank
                LIMIT :limit
                """
            ),
            {"match_query": match_query, "limit": int(limit)},
        ).mappings().all()

    results: list[dict[str, Any]] = []
    for row in rows:
        item_id = str(row.get("item_id") or "")
        card = by_id.get(item_id)
        if not card:
            continue
        kcal = float(card.get("kcal") or card.get("label_kcal") or 0)
        if kcal == 0:
            import re as _re

            band = str(card.get("kcal_band") or "")
            single = _re.search(r"^\D*([\d.]+)\s*kcal", band, _re.IGNORECASE)
            if single:
                kcal = float(single.group(1))
            else:
                range_match = _re.search(r"(\d+)-(\d+)\s*kcal", band, _re.IGNORECASE)
                if range_match:
                    low, high = float(range_match.group(1)), float(range_match.group(2))
                    kcal = (low + high) / 2
        protein = float(card.get("protein_g") or 0)
        carb = float(card.get("carb_g") or 0)
        fat = float(card.get("fat_g") or 0)
        title = str(card.get("title") or "").strip()
        confidence = "high" if title and title in query else "medium"
        results.append(
            {
                "item_id": item_id,
                "title": str(card.get("title") or ""),
                "aliases": [str(item).strip() for item in card.get("aliases", []) if str(item).strip()],
                "brand": str(card.get("brand") or ""),
                "label_kcal": kcal,
                "label_macros": {
                    "protein_g": protein,
                    "carb_g": carb,
                    "fat_g": fat,
                },
                "serving_basis": str(card.get("serving_basis") or card.get("serving_size") or ""),
                "match_confidence": confidence,
                "source": "exact_item_db",
                "source_type": "exact_item_card",
                "source_class": "exact_item_db",
                "evidence_role": "exact_truth",
                "record_role": "exact_item",
                "identity_confidence": confidence,
                "portion_basis_quality": "strong",
                "estimate_eligibility": "exact",
                "macro_completeness": "complete",
                "provenance": {
                    "source_type": "exact_item_card",
                    "source_name": str(card.get("title") or ""),
                    "source_url": str(card.get("source_url") or ""),
                },
                "source_note": str(card.get("source_note") or ""),
                "protein_g": protein,
                "carb_g": carb,
                "fat_g": fat,
                "kcal": kcal,
            }
        )
    return results
