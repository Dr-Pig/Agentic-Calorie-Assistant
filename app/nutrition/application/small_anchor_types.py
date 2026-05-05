from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
