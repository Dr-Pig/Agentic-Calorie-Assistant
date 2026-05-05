from __future__ import annotations

from functools import lru_cache

from .context_normalizer import lookup_key
from .nutrition_evidence_store import NutritionEvidenceStorePort, default_nutrition_evidence_store
from .retrieval_intent import RetrievalIntent
from . import small_anchor_types as _small_anchor_types
from .small_anchor_index import (
    AnchorLookupIndex,
    build_anchor_lookup_index,
    match_indexed_anchor_candidates,
    match_indexed_semantic_only_support,
)
from .small_anchor_records import (
    anchor_records_from_items,
    candidate_from_record,
    semantic_support_from_item,
)

AnchorTruthLevel = _small_anchor_types.AnchorTruthLevel
AnchorSourcePosture = _small_anchor_types.AnchorSourcePosture
AnchorLookupContext = _small_anchor_types.AnchorLookupContext
AnchorSupportRole = _small_anchor_types.AnchorSupportRole
AnchorMutationAuthority = _small_anchor_types.AnchorMutationAuthority
AnchorDeferReason = _small_anchor_types.AnchorDeferReason
GenericRecordKind = _small_anchor_types.GenericRecordKind
GenericLookupMatchPath = _small_anchor_types.GenericLookupMatchPath
AnchorModifierSchema = _small_anchor_types.AnchorModifierSchema
AnchorRecord = _small_anchor_types.AnchorRecord
GenericClarifySupport = _small_anchor_types.GenericClarifySupport
AnchorCandidate = _small_anchor_types.AnchorCandidate
AnchorLookupResult = _small_anchor_types.AnchorLookupResult


def lookup_anchor_candidates(
    intent: RetrievalIntent,
    *,
    limit: int = 4,
    evidence_store: NutritionEvidenceStorePort | None = None,
) -> AnchorLookupResult:
    if evidence_store is None:
        store = default_nutrition_evidence_store()
        use_default_store = True
    else:
        store = evidence_store
        use_default_store = False
    retrieval_context: AnchorLookupContext = (
        "query_only_support" if intent.retrieval_goal == "query_only_answer" else "logging_support"
    )
    if intent.retrieval_goal == "exact_brand_lookup":
        return AnchorLookupResult((), retrieval_context, "none", "exact_brand_lookup_deferred_to_b2_005", None)

    query_texts = _query_texts_for_intent(intent)
    if intent.retrieval_goal == "listed_item_lookup":
        if len(intent.listed_items) != 1:
            return AnchorLookupResult((), retrieval_context, "none", "listed_item_fanout_deferred", None)
        query_texts = (intent.listed_items[0],)

    clarify_support = None
    if intent.retrieval_goal in {"composition_clarification", "query_only_answer"}:
        clarify_support = _match_semantic_only_support(
            query_texts,
            evidence_store=store,
            use_default_store=use_default_store,
        )
    if clarify_support is not None:
        return AnchorLookupResult((), retrieval_context, "none", None, clarify_support)

    if intent.retrieval_goal == "composition_clarification":
        return AnchorLookupResult((), retrieval_context, "none", "composition_clarification_deferred", None)

    candidates = tuple(
        _match_anchor_candidates(
            query_texts,
            limit=limit,
            evidence_store=store,
            use_default_store=use_default_store,
        )
    )
    if not candidates:
        return AnchorLookupResult((), retrieval_context, "none", "no_anchor_match", None)
    return AnchorLookupResult(candidates, retrieval_context, "none", None, None)


def _query_texts_for_intent(intent: RetrievalIntent) -> tuple[str, ...]:
    values: list[str] = []
    if intent.base_dish:
        values.append(intent.base_dish)
    values.extend(alias for alias in intent.aliases if alias)
    return tuple(values)


def _match_anchor_candidates(
    query_texts: tuple[str, ...],
    *,
    limit: int,
    evidence_store: NutritionEvidenceStorePort,
    use_default_store: bool,
) -> list[AnchorCandidate]:
    query_keys = _lookup_keys_for_texts(query_texts)
    if not query_keys:
        return []
    if use_default_store:
        return match_indexed_anchor_candidates(_load_default_anchor_lookup_index(), query_keys, limit=limit)

    matched: list[tuple[int, AnchorCandidate]] = []
    for record in _load_anchor_records(evidence_store):
        canonical_key = lookup_key(record.canonical_name)
        if canonical_key in query_keys:
            matched.append(
                (
                    0,
                    candidate_from_record(
                        record,
                        matched_alias=record.canonical_name,
                        match_path="canonical_name_exact",
                    ),
                )
            )
            continue
        for alias in record.aliases:
            if lookup_key(alias) in query_keys:
                matched.append(
                    (
                        1,
                        candidate_from_record(
                            record,
                            matched_alias=alias,
                            match_path="alias_exact",
                        ),
                    )
                )
                break

    matched.sort(key=lambda item: (item[0], item[1].canonical_name))
    return [candidate for _, candidate in matched[:limit]]


def _match_semantic_only_support(
    query_texts: tuple[str, ...],
    *,
    evidence_store: NutritionEvidenceStorePort,
    use_default_store: bool,
) -> GenericClarifySupport | None:
    query_keys = _lookup_keys_for_texts(query_texts)
    if not query_keys:
        return None
    if use_default_store:
        return match_indexed_semantic_only_support(_load_default_anchor_lookup_index(), query_keys)
    return _scan_semantic_only_support(query_keys, evidence_store=evidence_store)


def _scan_semantic_only_support(
    query_keys: set[str],
    *,
    evidence_store: NutritionEvidenceStorePort,
) -> GenericClarifySupport | None:
    for item in evidence_store.load_small_anchor_records():
        support = semantic_support_from_item(item, query_keys)
        if support is not None:
            return support
    return None


def _lookup_keys_for_texts(query_texts: tuple[str, ...]) -> set[str]:
    keys: set[str] = set()
    for text in query_texts:
        key = lookup_key(text)
        if key:
            keys.add(key)
    return keys


@lru_cache(maxsize=1)
def _load_default_small_anchor_items() -> tuple[dict[str, object], ...]:
    return tuple(default_nutrition_evidence_store().load_small_anchor_records())


@lru_cache(maxsize=1)
def _load_default_anchor_records() -> tuple[AnchorRecord, ...]:
    return anchor_records_from_items(_load_default_small_anchor_items())


@lru_cache(maxsize=1)
def _load_default_anchor_lookup_index() -> AnchorLookupIndex:
    return build_anchor_lookup_index(
        _load_default_anchor_records(),
        semantic_items=_load_default_small_anchor_items(),
    )


def _load_anchor_records(evidence_store: NutritionEvidenceStorePort) -> tuple[AnchorRecord, ...]:
    return anchor_records_from_items(evidence_store.load_small_anchor_records())


__all__ = [
    "AnchorCandidate",
    "AnchorDeferReason",
    "AnchorLookupResult",
    "AnchorModifierSchema",
    "AnchorRecord",
    "GenericClarifySupport",
    "lookup_anchor_candidates",
]
