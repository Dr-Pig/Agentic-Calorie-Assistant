from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .exact_item_card_lookup import ExactItemCardCandidate, ExactItemCardLookupResult
from .small_anchor_store import AnchorCandidate, AnchorLookupResult

PacketSeedCandidateKind = Literal["generic_anchor", "exact_item_card"]
PacketSeedPacketType = Literal["GenericDbCandidatePacket", "ExactDbCandidatePacket"]
PacketSeedSourceType = Literal["generic_db", "exact_db"]
PacketSeedMatchType = Literal["generic", "exact", "alias_exact"]

_ANCHOR_RAW_REF_PREFIX = "app/knowledge/small_anchor_store_tw.json#"
_EXACT_ITEM_RAW_REF_PREFIX = "app/knowledge/exact_item_cards_tw.json#"


@dataclass(frozen=True)
class PacketizerInputSeed:
    candidate_kind: PacketSeedCandidateKind
    packet_type: PacketSeedPacketType
    source_type: PacketSeedSourceType
    matched_name: str
    canonical_name: str
    match_type: PacketSeedMatchType
    serving_basis: str
    raw_ref: str
    dish_type: str | None = None
    composition_posture: str | None = None
    variance_level: str | None = None
    semantic_hints: tuple[str, ...] = ()
    followup_hints: tuple[str, ...] = ()
    clarify_required: bool = False
    kcal_range: tuple[int, int] | None = None
    likely_kcal: int | None = None
    kcal: float | None = None
    kcal_band: str | None = None


def packetizer_input_seed_from_anchor_candidate(candidate: AnchorCandidate) -> PacketizerInputSeed:
    return PacketizerInputSeed(
        candidate_kind="generic_anchor",
        packet_type="GenericDbCandidatePacket",
        source_type="generic_db",
        matched_name=candidate.matched_alias,
        canonical_name=candidate.canonical_name,
        match_type="generic",
        serving_basis="common_serving",
        raw_ref=f"{_ANCHOR_RAW_REF_PREFIX}{candidate.anchor_id}",
        dish_type=candidate.dish_type,
        composition_posture=candidate.composition_posture,
        variance_level=candidate.variance_level,
        semantic_hints=candidate.semantic_hints,
        followup_hints=candidate.followup_hints,
        clarify_required=candidate.clarify_required,
        kcal_range=candidate.baseline_kcal_range,
        likely_kcal=candidate.baseline_likely_kcal,
    )


def packetizer_input_seeds_from_anchor_lookup_result(
    result: AnchorLookupResult,
) -> tuple[PacketizerInputSeed, ...]:
    if result.defer_reason is not None or result.clarify_support is not None:
        return ()
    return tuple(packetizer_input_seed_from_anchor_candidate(candidate) for candidate in result.candidates)


def packetizer_input_seed_from_exact_item_card_candidate(
    candidate: ExactItemCardCandidate,
) -> PacketizerInputSeed:
    return PacketizerInputSeed(
        candidate_kind="exact_item_card",
        packet_type="ExactDbCandidatePacket",
        source_type="exact_db",
        matched_name=candidate.matched_query,
        canonical_name=candidate.title,
        match_type="exact" if candidate.match_path == "exact_title" else "alias_exact",
        serving_basis=candidate.serving_basis,
        raw_ref=f"{_EXACT_ITEM_RAW_REF_PREFIX}{candidate.item_id}",
        kcal=candidate.kcal,
        kcal_band=candidate.kcal_band,
    )


def packetizer_input_seeds_from_exact_item_lookup_result(
    result: ExactItemCardLookupResult,
) -> tuple[PacketizerInputSeed, ...]:
    if result.defer_reason is not None:
        return ()
    return tuple(packetizer_input_seed_from_exact_item_card_candidate(candidate) for candidate in result.candidates)


__all__ = [
    "PacketizerInputSeed",
    "packetizer_input_seed_from_anchor_candidate",
    "packetizer_input_seed_from_exact_item_card_candidate",
    "packetizer_input_seeds_from_anchor_lookup_result",
    "packetizer_input_seeds_from_exact_item_lookup_result",
]
