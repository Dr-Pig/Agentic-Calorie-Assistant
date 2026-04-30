from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .context_normalizer import lookup_key
from .nutrition_evidence_store import NutritionEvidenceStorePort, default_nutrition_evidence_store
from .retrieval_intent import RetrievalIntent

ExactItemCardDeferReason = Literal[
    "unsupported_retrieval_goal",
    "no_exact_item_match",
    "metadata_filtered_all_candidates",
]
ExactItemCardMatchPath = Literal["exact_title", "exact_alias"]


@dataclass(frozen=True)
class ExactItemCardCandidate:
    item_id: str
    title: str
    aliases: tuple[str, ...]
    brand: str
    serving_basis: str
    kcal: float | None
    kcal_band: str | None
    match_path: ExactItemCardMatchPath
    matched_query: str
    filters_applied: tuple[str, ...]
    source: Literal["local_exact_item_seed"]
    support_only: Literal[True]


@dataclass(frozen=True)
class ExactItemCardLookupResult:
    candidates: tuple[ExactItemCardCandidate, ...]
    defer_reason: ExactItemCardDeferReason | None


def lookup_exact_item_card_candidates(
    intent: RetrievalIntent,
    *,
    limit: int = 5,
    evidence_store: NutritionEvidenceStorePort | None = None,
) -> ExactItemCardLookupResult:
    store = evidence_store or default_nutrition_evidence_store()
    if intent.retrieval_goal not in {"exact_brand_lookup", "query_only_answer"}:
        return ExactItemCardLookupResult((), "unsupported_retrieval_goal")
    if intent.retrieval_goal == "query_only_answer" and not intent.brand_hint:
        return ExactItemCardLookupResult((), "unsupported_retrieval_goal")

    raw_matches = _find_raw_matches(intent, evidence_store=store)
    if not raw_matches:
        return ExactItemCardLookupResult((), "no_exact_item_match")

    filtered_matches, filters_applied = _apply_metadata_filters(raw_matches, intent)
    if not filtered_matches:
        return ExactItemCardLookupResult((), "metadata_filtered_all_candidates")

    candidates = tuple(
        _candidate_from_match(match, filters_applied=filters_applied) for match in filtered_matches[:limit]
    )
    return ExactItemCardLookupResult(candidates, None)


def _find_raw_matches(
    intent: RetrievalIntent,
    *,
    evidence_store: NutritionEvidenceStorePort,
) -> list[dict[str, object]]:
    query_texts = _query_texts_for_intent(intent)
    query_keys = [(text, lookup_key(text)) for text in query_texts if lookup_key(text)]
    matches: list[dict[str, object]] = []
    for record in evidence_store.load_exact_item_card_records():
        title = str(record.get("title") or "").strip()
        title_key = lookup_key(title)
        aliases = [str(alias).strip() for alias in record.get("aliases", []) if str(alias).strip()]
        alias_keys = [(alias, lookup_key(alias)) for alias in aliases if lookup_key(alias)]
        for query_text, query_key in query_keys:
            if query_key == title_key:
                matches.append(
                    {
                        "record": record,
                        "match_path": "exact_title",
                        "matched_query": query_text,
                    }
                )
                break
            alias_match = next((alias for alias, alias_key in alias_keys if alias_key == query_key), None)
            if alias_match is not None:
                matches.append(
                    {
                        "record": record,
                        "match_path": "exact_alias",
                        "matched_query": query_text,
                    }
                )
                break
    matches.sort(key=lambda item: (str(item["match_path"]), str(item["record"].get("title") or "")))
    return matches


def _query_texts_for_intent(intent: RetrievalIntent) -> tuple[str, ...]:
    values: list[str] = []
    if intent.base_dish:
        values.append(intent.base_dish)
    values.extend(alias for alias in intent.aliases if alias)
    if intent.brand_hint and intent.base_dish:
        values.append(f"{intent.brand_hint}{intent.base_dish}")
        if intent.size_hint:
            values.append(f"{intent.brand_hint}{intent.base_dish}{intent.size_hint}")
    return tuple(dict.fromkeys(values))


def _apply_metadata_filters(
    matches: list[dict[str, object]],
    intent: RetrievalIntent,
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    filtered = list(matches)
    applied: list[str] = []
    if intent.brand_hint:
        applied.append("brand_hint")
        filtered = [
            item
            for item in filtered
            if intent.brand_hint in str((item["record"] or {}).get("brand") or "")
        ]
    if intent.size_hint:
        applied.append("size_hint")
        filtered = [
            item
            for item in filtered
            if _record_matches_size_hint(item["record"], intent.size_hint)
        ]
    return filtered, tuple(applied)


def _record_matches_size_hint(record: object, size_hint: str) -> bool:
    payload = dict(record or {})
    haystacks = [
        str(payload.get("title") or ""),
        str(payload.get("serving_basis") or ""),
        *[str(alias) for alias in payload.get("aliases", []) if str(alias).strip()],
    ]
    hint_key = lookup_key(size_hint)
    return any(lookup_key(text) == hint_key or hint_key in lookup_key(text) for text in haystacks if lookup_key(text))


def _candidate_from_match(
    match: dict[str, object],
    *,
    filters_applied: tuple[str, ...],
) -> ExactItemCardCandidate:
    record = dict(match["record"] or {})
    kcal_value = record.get("kcal")
    kcal = float(kcal_value) if isinstance(kcal_value, (int, float)) else None
    kcal_band = str(record.get("kcal_band") or "").strip() or None
    return ExactItemCardCandidate(
        item_id=str(record.get("item_id") or "").strip(),
        title=str(record.get("title") or "").strip(),
        aliases=tuple(str(alias).strip() for alias in record.get("aliases", []) if str(alias).strip()),
        brand=str(record.get("brand") or "").strip(),
        serving_basis=str(record.get("serving_basis") or "").strip(),
        kcal=kcal,
        kcal_band=kcal_band,
        match_path=str(match["match_path"]),
        matched_query=str(match["matched_query"]),
        filters_applied=filters_applied,
        source="local_exact_item_seed",
        support_only=True,
    )


__all__ = [
    "ExactItemCardCandidate",
    "ExactItemCardLookupResult",
    "lookup_exact_item_card_candidates",
]
