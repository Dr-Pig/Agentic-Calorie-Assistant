from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from .context_normalizer import lookup_key
from .retrieval_intent import RetrievalIntent
from ..infrastructure.small_anchor_store_loader import load_small_anchor_seed_records

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


def lookup_anchor_candidates(
    intent: RetrievalIntent,
    *,
    limit: int = 4,
) -> AnchorLookupResult:
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

    clarify_support = _match_semantic_only_support(query_texts)
    if clarify_support is not None:
        return AnchorLookupResult((), retrieval_context, "none", None, clarify_support)

    if intent.retrieval_goal == "composition_clarification":
        return AnchorLookupResult((), retrieval_context, "none", "composition_clarification_deferred", None)

    candidates = tuple(_match_anchor_candidates(query_texts, limit=limit))
    if not candidates:
        return AnchorLookupResult((), retrieval_context, "none", "no_anchor_match", None)
    return AnchorLookupResult(candidates, retrieval_context, "none", None, None)


def _query_texts_for_intent(intent: RetrievalIntent) -> tuple[str, ...]:
    values: list[str] = []
    if intent.base_dish:
        values.append(intent.base_dish)
    values.extend(alias for alias in intent.aliases if alias)
    return tuple(values)


def _match_anchor_candidates(query_texts: tuple[str, ...], *, limit: int) -> list[AnchorCandidate]:
    query_keys = {lookup_key(text) for text in query_texts if lookup_key(text)}
    if not query_keys:
        return []

    matched: list[tuple[int, AnchorCandidate]] = []
    for record in _load_anchor_records():
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


def _match_semantic_only_support(query_texts: tuple[str, ...]) -> GenericClarifySupport | None:
    query_keys = {lookup_key(text) for text in query_texts if lookup_key(text)}
    if not query_keys:
        return None

    for item in load_small_anchor_seed_records():
        if str(item.get("record_kind") or "").strip() != "generic_semantic_only":
            continue
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


@lru_cache(maxsize=1)
def _load_anchor_records() -> tuple[AnchorRecord, ...]:
    records: list[AnchorRecord] = []
    for item in load_small_anchor_seed_records():
        if str(item.get("record_kind") or "generic_anchor").strip() != "generic_anchor":
            continue
        modifiers = tuple(
            AnchorModifierSchema(
                name=str(modifier.get("name") or "").strip(),
                values=tuple(str(value).strip() for value in modifier.get("values", []) if str(value).strip()),
            )
            for modifier in item.get("major_modifiers", [])
            if str(modifier.get("name") or "").strip()
        )
        kcal_range = item.get("baseline_kcal_range") or [0, 0]
        low = int(kcal_range[0]) if len(kcal_range) > 0 else 0
        high = int(kcal_range[1]) if len(kcal_range) > 1 else low
        records.append(
            AnchorRecord(
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
                major_modifiers=modifiers,
                composition_hints=_tuple_texts(item.get("composition_hints", [])),
            )
        )
    return tuple(records)


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
