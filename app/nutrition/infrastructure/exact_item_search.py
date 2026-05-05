from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .exact_item_card_loader import load_exact_item_card_seed_records

_SINGLE_KCAL_RE = re.compile(r"^\D*([\d.]+)\s*kcal", re.IGNORECASE)
_RANGE_KCAL_RE = re.compile(r"(\d+)-(\d+)\s*kcal", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_cards() -> list[dict[str, Any]]:
    return list(load_exact_item_card_seed_records())


@lru_cache(maxsize=1)
def _cards_by_id() -> dict[str, dict[str, Any]]:
    cards_by_id: dict[str, dict[str, Any]] = {}
    for card in _load_cards():
        item_id = _card_item_id(card)
        if item_id:
            cards_by_id[item_id] = card
    return cards_by_id


@lru_cache(maxsize=1)
def _local_seed_engine() -> Engine:
    return create_engine("sqlite:///:memory:")


def _card_item_id(card: dict[str, Any]) -> str:
    return str(card.get("card_id") or card.get("id") or card.get("item_id") or "")


def _card_aliases_text(card: dict[str, Any]) -> str:
    return " ".join(str(item).strip() for item in card.get("aliases", []) if str(item).strip())


def _card_aliases_list(card: dict[str, Any]) -> list[str]:
    return [str(item).strip() for item in card.get("aliases", []) if str(item).strip()]


def _insert_exact_item_search_card(conn: Any, card: dict[str, Any]) -> None:
    conn.execute(
        text(
            """
            INSERT INTO exact_item_search(item_id, title, aliases, brand)
            VALUES (:item_id, :title, :aliases, :brand)
            """
        ),
        {
            "item_id": _card_item_id(card),
            "title": str(card.get("title") or ""),
            "aliases": _card_aliases_text(card),
            "brand": str(card.get("brand") or ""),
        },
    )


def ensure_exact_item_fts(*, engine: Engine | None = None) -> None:
    active_engine = engine or _local_seed_engine()

    cards = _load_cards()
    with active_engine.begin() as conn:
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
            _insert_exact_item_search_card(conn, card)


def _build_fts_match_query(query: str) -> str:
    escaped_terms = _escaped_fts_terms(query)
    if len(escaped_terms) == 1 and escaped_terms[0].endswith("*"):
        return escaped_terms[0]
    if _has_prefix_fts_term(escaped_terms):
        return _quoted_fts_terms(escaped_terms, separator=" AND ")
    return _quoted_fts_terms(escaped_terms, separator=" OR ") or query


def _escaped_fts_terms(query: str) -> list[str]:
    return [term.replace('"', " ").strip() for term in query.split() if term.strip()]


def _has_prefix_fts_term(terms: list[str]) -> bool:
    return any(term.endswith("*") for term in terms)


def _quoted_fts_terms(terms: list[str], *, separator: str) -> str:
    return separator.join(f'"{term}"' for term in terms)


def _select_exact_item_rows(active_engine: Engine, match_query: str, limit: int) -> list[dict[str, Any]]:
    with active_engine.begin() as conn:
        return list(
            conn.execute(
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
            )
            .mappings()
            .all()
        )


def _parse_label_kcal(card: dict[str, Any]) -> float:
    kcal = float(card.get("kcal") or card.get("label_kcal") or 0)
    if kcal != 0:
        return kcal

    return _parse_kcal_band(str(card.get("kcal_band") or ""), fallback=kcal)


def _parse_kcal_band(band: str, *, fallback: float) -> float:
    single = _SINGLE_KCAL_RE.search(band)
    if single:
        return float(single.group(1))

    range_match = _RANGE_KCAL_RE.search(band)
    if not range_match:
        return fallback

    low, high = float(range_match.group(1)), float(range_match.group(2))
    return (low + high) / 2


def _match_confidence(card: dict[str, Any], query: str) -> str:
    title = str(card.get("title") or "").strip()
    return "high" if title and title in query else "medium"


def _card_macro_values(card: dict[str, Any]) -> tuple[float, float, float]:
    protein = float(card.get("protein_g") or 0)
    carb = float(card.get("carb_g") or 0)
    fat = float(card.get("fat_g") or 0)
    return protein, carb, fat


def _label_macros_payload(protein: float, carb: float, fat: float) -> dict[str, float]:
    return {
        "protein_g": protein,
        "carb_g": carb,
        "fat_g": fat,
    }


def _card_serving_basis(card: dict[str, Any]) -> str:
    return str(card.get("serving_basis") or card.get("serving_size") or "")


def _source_provenance(card: dict[str, Any]) -> dict[str, str]:
    return {
        "source_type": "exact_item_card",
        "source_name": str(card.get("title") or ""),
        "source_url": str(card.get("source_url") or ""),
    }


def _shape_exact_item_result(item_id: str, card: dict[str, Any], query: str) -> dict[str, Any]:
    kcal = _parse_label_kcal(card)
    protein, carb, fat = _card_macro_values(card)
    confidence = _match_confidence(card, query)
    return {
        "item_id": item_id,
        "title": str(card.get("title") or ""),
        "aliases": _card_aliases_list(card),
        "brand": str(card.get("brand") or ""),
        "label_kcal": kcal,
        "label_macros": _label_macros_payload(protein, carb, fat),
        "serving_basis": _card_serving_basis(card),
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
        "provenance": _source_provenance(card),
        "source_note": str(card.get("source_note") or ""),
        "protein_g": protein,
        "carb_g": carb,
        "fat_g": fat,
        "kcal": kcal,
    }


def resolve_exact_item_fts(query: str, *, limit: int = 3, engine: Engine | None = None) -> list[dict[str, Any]]:
    active_engine = engine or _local_seed_engine()

    ensure_exact_item_fts(engine=active_engine)
    query = str(query or "").strip()
    if not query:
        return []
    by_id = _cards_by_id()
    rows = _select_exact_item_rows(active_engine, _build_fts_match_query(query), limit)

    results: list[dict[str, Any]] = []
    for row in rows:
        item_id = str(row.get("item_id") or "")
        card = by_id.get(item_id)
        if not card:
            continue
        results.append(_shape_exact_item_result(item_id, card, query))
    return results
