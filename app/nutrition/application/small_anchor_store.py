from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from .context_normalizer import lookup_key
from .nutrition_evidence_store import NutritionEvidenceStorePort, default_nutrition_evidence_store
from .retrieval_intent import RetrievalIntent

AnchorTruthLevel = Literal["anchor"]
AnchorSourcePosture = Literal["generic_anchor_seed"]
AnchorLookupContext = Literal["logging_support", "query_only_support"]
AnchorSupportRole = Literal["lookup_support_only"]
AnchorMutationAuthority = Literal["none"]
AnchorDeferReason = Literal[
    "composition_clarification_deferred",
    "exact_brand_lookup_deferred_to_b2_005",
    "no_anchor_match",
    "listed_item_fanout_deferred",
]
GenericRecordKind = Literal["generic_anchor", "generic_semantic_only"]
GenericLookupMatchPath = Literal["canonical_name_exact", "alias_exact"]


@dataclass(frozen=True)
class AnchorModifierSchema:
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class AnchorRecord:
    record_kind: Literal["generic_anchor"]
    anchor_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    dish_type: str
    composition_posture: str | None
    variance_level: str | None
    semantic_hints: tuple[str, ...]
    followup_hints: tuple[str, ...]
    clarify_required: bool
    source_posture: AnchorSourcePosture
    baseline_kcal_range: tuple[int, int]
    baseline_likely_kcal: int
    major_modifiers: tuple[AnchorModifierSchema, ...]
    composition_hints: tuple[str, ...]


@dataclass(frozen=True)
class GenericClarifySupport:
    record_kind: Literal["generic_semantic_only"]
    canonical_name: str
    matched_alias: str
    dish_type: str | None
    composition_posture: str | None
    variance_level: str | None
    semantic_hints: tuple[str, ...]
    followup_hints: tuple[str, ...]
    clarify_required: Literal[True]
    unresolved_reason: str | None
    match_path: GenericLookupMatchPath


@dataclass(frozen=True)
class AnchorCandidate:
    anchor_id: str
    canonical_name: str
    matched_alias: str
    dish_type: str
    composition_posture: str | None
    variance_level: str | None
    semantic_hints: tuple[str, ...]
    followup_hints: tuple[str, ...]
    clarify_required: bool
    source_posture: AnchorSourcePosture
    truth_level: AnchorTruthLevel
    support_role: AnchorSupportRole
    baseline_kcal_range: tuple[int, int]
    baseline_likely_kcal: int
    major_modifiers: tuple[AnchorModifierSchema, ...]
    composition_hints: tuple[str, ...]
    match_path: GenericLookupMatchPath


@dataclass(frozen=True)
class AnchorLookupResult:
    candidates: tuple[AnchorCandidate, ...]
    retrieval_context: AnchorLookupContext
    mutation_authority: AnchorMutationAuthority
    defer_reason: AnchorDeferReason | None
    clarify_support: GenericClarifySupport | None


@dataclass(frozen=True)
class _AnchorIndexEntry:
    record_order: int
    alias_order: int
    rank: int
    candidate: AnchorCandidate


@dataclass(frozen=True)
class _SemanticSupportIndexEntry:
    record_order: int
    alias_order: int
    rank: int
    support: GenericClarifySupport


@dataclass(frozen=True)
class _AnchorLookupIndex:
    anchor_canonical: dict[str, tuple[_AnchorIndexEntry, ...]]
    anchor_aliases: dict[str, tuple[_AnchorIndexEntry, ...]]
    semantic_support: dict[str, tuple[_SemanticSupportIndexEntry, ...]]


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
        return _match_default_anchor_candidates(query_keys, limit=limit)

    matched: list[tuple[int, AnchorCandidate]] = []
    for record in _load_anchor_records(evidence_store):
        canonical_key = lookup_key(record.canonical_name)
        if canonical_key in query_keys:
            matched.append(
                (
                    0,
                    _candidate_from_record(
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
                        _candidate_from_record(
                            record,
                            matched_alias=alias,
                            match_path="alias_exact",
                        ),
                    )
                )
                break

    matched.sort(key=lambda item: (item[0], item[1].canonical_name))
    return [candidate for _, candidate in matched[:limit]]


def _match_default_anchor_candidates(query_keys: set[str], *, limit: int) -> list[AnchorCandidate]:
    index = _load_default_anchor_lookup_index()
    matched: dict[int, _AnchorIndexEntry] = {}
    for key in query_keys:
        for entry in index.anchor_canonical.get(key, ()):
            _keep_best_anchor_entry(matched, entry)
    for key in query_keys:
        for entry in index.anchor_aliases.get(key, ()):
            _keep_best_anchor_entry(matched, entry)

    ordered = sorted(
        matched.values(),
        key=lambda entry: (entry.rank, entry.record_order, entry.alias_order),
    )
    return [entry.candidate for entry in ordered[:limit]]


def _keep_best_anchor_entry(matched: dict[int, _AnchorIndexEntry], entry: _AnchorIndexEntry) -> None:
    current = matched.get(entry.record_order)
    if current is None or (entry.rank, entry.alias_order) < (current.rank, current.alias_order):
        matched[entry.record_order] = entry


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
        return _match_default_semantic_only_support(query_keys)

    return _scan_semantic_only_support(query_keys, evidence_store=evidence_store)


def _scan_semantic_only_support(
    query_keys: set[str],
    *,
    evidence_store: NutritionEvidenceStorePort,
) -> GenericClarifySupport | None:
    for item in evidence_store.load_small_anchor_records():
        support = _semantic_support_from_item(item, query_keys)
        if support is not None:
            return support
    return None


def _semantic_support_from_item(
    item: dict[str, object],
    query_keys: set[str],
) -> GenericClarifySupport | None:
    if str(item.get("record_kind") or "").strip() != "generic_semantic_only":
        return None
    canonical_name = str(item.get("canonical_name") or "").strip()
    canonical_key = lookup_key(canonical_name)
    if canonical_key in query_keys:
        return _clarify_support_from_item(
            item,
            matched_alias=canonical_name,
            match_path="canonical_name_exact",
        )
    aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
    for alias in aliases:
        if lookup_key(alias) in query_keys:
            return _clarify_support_from_item(
                item,
                matched_alias=alias,
                match_path="alias_exact",
            )
    return None


def _match_default_semantic_only_support(query_keys: set[str]) -> GenericClarifySupport | None:
    index = _load_default_anchor_lookup_index()
    matches = [entry for key in query_keys for entry in index.semantic_support.get(key, ())]
    if not matches:
        return None
    return min(matches, key=lambda entry: (entry.record_order, entry.rank, entry.alias_order)).support


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
    return _anchor_records_from_items(_load_default_small_anchor_items())


@lru_cache(maxsize=1)
def _load_default_anchor_lookup_index() -> _AnchorLookupIndex:
    return _build_anchor_lookup_index(
        _load_default_anchor_records(),
        semantic_items=_load_default_small_anchor_items(),
    )


def _load_anchor_records(evidence_store: NutritionEvidenceStorePort) -> tuple[AnchorRecord, ...]:
    return _anchor_records_from_items(evidence_store.load_small_anchor_records())


def _build_anchor_lookup_index(
    records: tuple[AnchorRecord, ...],
    *,
    semantic_items: tuple[dict[str, object], ...],
) -> _AnchorLookupIndex:
    anchor_canonical: dict[str, list[_AnchorIndexEntry]] = {}
    anchor_aliases: dict[str, list[_AnchorIndexEntry]] = {}
    semantic_support: dict[str, list[_SemanticSupportIndexEntry]] = {}

    for record_order, record in enumerate(records):
        _index_anchor_record(record, record_order, anchor_canonical, anchor_aliases)

    for record_order, item in enumerate(semantic_items):
        _index_semantic_support_item(item, record_order, semantic_support)

    return _AnchorLookupIndex(
        anchor_canonical={key: tuple(entries) for key, entries in anchor_canonical.items()},
        anchor_aliases={key: tuple(entries) for key, entries in anchor_aliases.items()},
        semantic_support={key: tuple(entries) for key, entries in semantic_support.items()},
    )


def _index_anchor_record(
    record: AnchorRecord,
    record_order: int,
    anchor_canonical: dict[str, list[_AnchorIndexEntry]],
    anchor_aliases: dict[str, list[_AnchorIndexEntry]],
) -> None:
    canonical_key = lookup_key(record.canonical_name)
    if canonical_key:
        anchor_canonical.setdefault(canonical_key, []).append(
            _AnchorIndexEntry(
                record_order=record_order,
                alias_order=-1,
                rank=0,
                candidate=_candidate_from_record(
                    record,
                    matched_alias=record.canonical_name,
                    match_path="canonical_name_exact",
                ),
            )
        )
    for alias_order, alias in enumerate(record.aliases):
        alias_key = lookup_key(alias)
        if not alias_key:
            continue
        anchor_aliases.setdefault(alias_key, []).append(
            _AnchorIndexEntry(
                record_order=record_order,
                alias_order=alias_order,
                rank=1,
                candidate=_candidate_from_record(
                    record,
                    matched_alias=alias,
                    match_path="alias_exact",
                ),
            )
        )


def _index_semantic_support_item(
    item: dict[str, object],
    record_order: int,
    semantic_support: dict[str, list[_SemanticSupportIndexEntry]],
) -> None:
    if str(item.get("record_kind") or "").strip() != "generic_semantic_only":
        return
    canonical_name = str(item.get("canonical_name") or "").strip()
    canonical_key = lookup_key(canonical_name)
    if canonical_key:
        semantic_support.setdefault(canonical_key, []).append(
            _SemanticSupportIndexEntry(
                record_order=record_order,
                alias_order=-1,
                rank=0,
                support=_clarify_support_from_item(
                    item,
                    matched_alias=canonical_name,
                    match_path="canonical_name_exact",
                ),
            )
        )
    aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
    for alias_order, alias in enumerate(aliases):
        alias_key = lookup_key(alias)
        if not alias_key:
            continue
        semantic_support.setdefault(alias_key, []).append(
            _SemanticSupportIndexEntry(
                record_order=record_order,
                alias_order=alias_order,
                rank=1,
                support=_clarify_support_from_item(
                    item,
                    matched_alias=alias,
                    match_path="alias_exact",
                ),
            )
        )


def _anchor_records_from_items(items: object) -> tuple[AnchorRecord, ...]:
    records: list[AnchorRecord] = []
    for item in items or []:
        record = _anchor_record_from_item(item)
        if record is not None:
            records.append(record)
    return tuple(records)


def _anchor_record_from_item(item: dict[str, object]) -> AnchorRecord | None:
    if str(item.get("record_kind") or "generic_anchor").strip() != "generic_anchor":
        return None
    low, high = _baseline_kcal_range(item.get("baseline_kcal_range") or [0, 0])
    return AnchorRecord(
        record_kind="generic_anchor",
        anchor_id=str(item.get("anchor_id") or "").strip(),
        canonical_name=str(item.get("canonical_name") or "").strip(),
        aliases=tuple(str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()),
        dish_type=str(item.get("dish_type") or "").strip(),
        composition_posture=_optional_text(item.get("composition_posture")),
        variance_level=_optional_text(item.get("variance_level")),
        semantic_hints=_tuple_texts(item.get("semantic_hints", [])),
        followup_hints=_tuple_texts(item.get("followup_hints", [])),
        clarify_required=bool(item.get("clarify_required") is True),
        source_posture="generic_anchor_seed",
        baseline_kcal_range=(low, high),
        baseline_likely_kcal=int(item.get("baseline_likely_kcal") or 0),
        major_modifiers=_modifier_schemas_from_items(item.get("major_modifiers", [])),
        composition_hints=_tuple_texts(item.get("composition_hints", [])),
    )


def _modifier_schemas_from_items(values: object) -> tuple[AnchorModifierSchema, ...]:
    return tuple(
        AnchorModifierSchema(
            name=str(modifier.get("name") or "").strip(),
            values=tuple(str(value).strip() for value in modifier.get("values", []) if str(value).strip()),
        )
        for modifier in values
        if str(modifier.get("name") or "").strip()
    )


def _baseline_kcal_range(kcal_range: object) -> tuple[int, int]:
    low = int(kcal_range[0]) if len(kcal_range) > 0 else 0
    high = int(kcal_range[1]) if len(kcal_range) > 1 else low
    return low, high


def _candidate_from_record(
    record: AnchorRecord,
    *,
    matched_alias: str,
    match_path: GenericLookupMatchPath,
) -> AnchorCandidate:
    return AnchorCandidate(
        anchor_id=record.anchor_id,
        canonical_name=record.canonical_name,
        matched_alias=matched_alias,
        dish_type=record.dish_type,
        composition_posture=record.composition_posture,
        variance_level=record.variance_level,
        semantic_hints=record.semantic_hints,
        followup_hints=record.followup_hints,
        clarify_required=record.clarify_required,
        source_posture=record.source_posture,
        truth_level="anchor",
        support_role="lookup_support_only",
        baseline_kcal_range=record.baseline_kcal_range,
        baseline_likely_kcal=record.baseline_likely_kcal,
        major_modifiers=record.major_modifiers,
        composition_hints=record.composition_hints,
        match_path=match_path,
    )


def _clarify_support_from_item(
    item: dict[str, object],
    *,
    matched_alias: str,
    match_path: GenericLookupMatchPath,
) -> GenericClarifySupport:
    return GenericClarifySupport(
        record_kind="generic_semantic_only",
        canonical_name=str(item.get("canonical_name") or "").strip(),
        matched_alias=matched_alias,
        dish_type=_optional_text(item.get("dish_type")),
        composition_posture=_optional_text(item.get("composition_posture")),
        variance_level=_optional_text(item.get("variance_level")),
        semantic_hints=_tuple_texts(item.get("semantic_hints", [])),
        followup_hints=_tuple_texts(item.get("followup_hints", [])),
        clarify_required=True,
        unresolved_reason=_optional_text(item.get("unresolved_reason")),
        match_path=match_path,
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _tuple_texts(values: object) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values or [] if str(value).strip())


__all__ = [
    "AnchorCandidate",
    "AnchorDeferReason",
    "AnchorLookupResult",
    "AnchorModifierSchema",
    "AnchorRecord",
    "GenericClarifySupport",
    "lookup_anchor_candidates",
]
