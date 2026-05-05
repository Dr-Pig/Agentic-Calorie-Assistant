from __future__ import annotations

from dataclasses import dataclass

from .context_normalizer import lookup_key
from .small_anchor_records import candidate_from_record, clarify_support_from_item
from .small_anchor_types import AnchorCandidate, AnchorRecord, GenericClarifySupport


@dataclass(frozen=True)
class AnchorIndexEntry:
    record_order: int
    alias_order: int
    rank: int
    candidate: AnchorCandidate


@dataclass(frozen=True)
class SemanticSupportIndexEntry:
    record_order: int
    alias_order: int
    rank: int
    support: GenericClarifySupport


@dataclass(frozen=True)
class AnchorLookupIndex:
    anchor_canonical: dict[str, tuple[AnchorIndexEntry, ...]]
    anchor_aliases: dict[str, tuple[AnchorIndexEntry, ...]]
    semantic_support: dict[str, tuple[SemanticSupportIndexEntry, ...]]


def build_anchor_lookup_index(
    records: tuple[AnchorRecord, ...],
    *,
    semantic_items: tuple[dict[str, object], ...],
) -> AnchorLookupIndex:
    anchor_canonical: dict[str, list[AnchorIndexEntry]] = {}
    anchor_aliases: dict[str, list[AnchorIndexEntry]] = {}
    semantic_support: dict[str, list[SemanticSupportIndexEntry]] = {}

    for record_order, record in enumerate(records):
        _index_anchor_record(record, record_order, anchor_canonical, anchor_aliases)

    for record_order, item in enumerate(semantic_items):
        _index_semantic_support_item(item, record_order, semantic_support)

    return AnchorLookupIndex(
        anchor_canonical={key: tuple(entries) for key, entries in anchor_canonical.items()},
        anchor_aliases={key: tuple(entries) for key, entries in anchor_aliases.items()},
        semantic_support={key: tuple(entries) for key, entries in semantic_support.items()},
    )


def match_indexed_anchor_candidates(
    index: AnchorLookupIndex,
    query_keys: set[str],
    *,
    limit: int,
) -> list[AnchorCandidate]:
    matched: dict[int, AnchorIndexEntry] = {}
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


def match_indexed_semantic_only_support(
    index: AnchorLookupIndex,
    query_keys: set[str],
) -> GenericClarifySupport | None:
    matches = [entry for key in query_keys for entry in index.semantic_support.get(key, ())]
    if not matches:
        return None
    return min(matches, key=lambda entry: (entry.record_order, entry.rank, entry.alias_order)).support


def _keep_best_anchor_entry(matched: dict[int, AnchorIndexEntry], entry: AnchorIndexEntry) -> None:
    current = matched.get(entry.record_order)
    if current is None or (entry.rank, entry.alias_order) < (current.rank, current.alias_order):
        matched[entry.record_order] = entry


def _index_anchor_record(
    record: AnchorRecord,
    record_order: int,
    anchor_canonical: dict[str, list[AnchorIndexEntry]],
    anchor_aliases: dict[str, list[AnchorIndexEntry]],
) -> None:
    canonical_key = lookup_key(record.canonical_name)
    if canonical_key:
        anchor_canonical.setdefault(canonical_key, []).append(
            AnchorIndexEntry(
                record_order=record_order,
                alias_order=-1,
                rank=0,
                candidate=candidate_from_record(
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
            AnchorIndexEntry(
                record_order=record_order,
                alias_order=alias_order,
                rank=1,
                candidate=candidate_from_record(
                    record,
                    matched_alias=alias,
                    match_path="alias_exact",
                ),
            )
        )


def _index_semantic_support_item(
    item: dict[str, object],
    record_order: int,
    semantic_support: dict[str, list[SemanticSupportIndexEntry]],
) -> None:
    if str(item.get("record_kind") or "").strip() != "generic_semantic_only":
        return
    canonical_name = str(item.get("canonical_name") or "").strip()
    canonical_key = lookup_key(canonical_name)
    if canonical_key:
        semantic_support.setdefault(canonical_key, []).append(
            SemanticSupportIndexEntry(
                record_order=record_order,
                alias_order=-1,
                rank=0,
                support=clarify_support_from_item(
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
            SemanticSupportIndexEntry(
                record_order=record_order,
                alias_order=alias_order,
                rank=1,
                support=clarify_support_from_item(
                    item,
                    matched_alias=alias,
                    match_path="alias_exact",
                ),
            )
        )
