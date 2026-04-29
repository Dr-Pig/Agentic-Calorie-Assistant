from __future__ import annotations

from typing import Sequence

from .packet_mismatch_oracles import exact_claim_mismatch_risks, packet_supports_exact_claim
from .packetizer_input_seed import PacketizerInputSeed


def build_candidate_packet(seed: PacketizerInputSeed) -> dict[str, object]:
    packet: dict[str, object] = {
        "packet_id": _packet_id_for_seed(seed),
        "packet_type": seed.packet_type,
        "truth_level": "candidate",
        "source_type": seed.source_type,
        "source_quality_label": _source_quality_label_for_seed(seed),
        "raw_ref": seed.raw_ref,
        "matched_name": seed.matched_name,
        "canonical_name": seed.canonical_name,
        "match_type": seed.match_type,
        "serving_basis": seed.serving_basis,
        "brand_match": _brand_match_for_seed(seed),
        "size_or_serving_match": _size_or_serving_match_for_seed(seed),
        "modifier_match": _modifier_match_for_seed(seed),
        "sibling_variant_risk": {"present": False, "reason": None},
    }
    if seed.dish_type is not None:
        packet["dish_type"] = seed.dish_type
    if seed.composition_posture is not None:
        packet["composition_posture"] = seed.composition_posture
    if seed.variance_level is not None:
        packet["variance_level"] = seed.variance_level
    if seed.semantic_hints:
        packet["semantic_hints"] = list(seed.semantic_hints)
    if seed.followup_hints:
        packet["followup_hints"] = list(seed.followup_hints)
    if seed.clarify_required:
        packet["clarify_required"] = True
    if seed.candidate_kind == "generic_anchor":
        if seed.kcal_range is not None:
            packet["kcal_range"] = seed.kcal_range
        if seed.likely_kcal is not None:
            packet["likely_kcal"] = seed.likely_kcal
    else:
        if seed.kcal is not None:
            packet["kcal"] = seed.kcal
        if seed.kcal_band is not None:
            packet["kcal_band"] = seed.kcal_band
    return packet


def build_candidate_packets(seeds: Sequence[PacketizerInputSeed]) -> tuple[dict[str, object], ...]:
    return tuple(build_candidate_packet(seed) for seed in seeds)


def add_hard_recheck_metadata(packet: dict[str, object]) -> dict[str, object]:
    enriched = dict(packet)
    enriched["hard_recheck_risks"] = list(exact_claim_mismatch_risks(enriched))
    enriched["supports_exact_claim"] = packet_supports_exact_claim(enriched)
    return enriched


def add_hard_recheck_metadata_many(
    packets: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    return tuple(add_hard_recheck_metadata(packet) for packet in packets)


def _packet_id_for_seed(seed: PacketizerInputSeed) -> str:
    seed_ref = _raw_ref_fragment(seed.raw_ref)
    if seed.candidate_kind == "generic_anchor":
        return f"pkt_generic_anchor_{seed_ref}"
    return f"pkt_exact_item_{seed_ref}"


def _raw_ref_fragment(raw_ref: str) -> str:
    _, _, fragment = raw_ref.partition("#")
    return fragment


def _source_quality_label_for_seed(seed: PacketizerInputSeed) -> str:
    if seed.candidate_kind == "generic_anchor":
        return "internal_generic"
    return "internal_exact"


def _brand_match_for_seed(seed: PacketizerInputSeed) -> str:
    if seed.candidate_kind == "generic_anchor":
        return "not_applicable"
    return "same"


def _size_or_serving_match_for_seed(seed: PacketizerInputSeed) -> str:
    if seed.candidate_kind == "generic_anchor":
        return "generic_serving"
    if str(seed.serving_basis or "").strip():
        return "same"
    return "unknown"


def _modifier_match_for_seed(seed: PacketizerInputSeed) -> str:
    if seed.candidate_kind == "generic_anchor":
        return "not_applicable"
    return "unknown"


__all__ = [
    "build_candidate_packet",
    "build_candidate_packets",
    "add_hard_recheck_metadata",
    "add_hard_recheck_metadata_many",
]
