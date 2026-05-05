from __future__ import annotations

import hashlib
from typing import Sequence

from .context_normalizer import lookup_key, lookup_tokens, normalize_text
from .retrieval_intent import RetrievalIntent
from .web_search_packetizer_policy import (
    SIZE_ALIAS_GROUPS as _SIZE_ALIAS_GROUPS,
    VARIANT_TOKENS as _VARIANT_TOKENS,
)


def build_web_search_candidate_packet(
    intent: RetrievalIntent,
    candidate: dict[str, object],
) -> dict[str, object]:
    requested_name = _requested_identity(intent, candidate)
    title = _text(candidate.get("source_title"))
    url = _text(candidate.get("source_url"))
    snippet = _text(candidate.get("snippet"))
    query = _text(candidate.get("query"))
    brand_detected = _text(candidate.get("brand_detected"))

    brand_match = _brand_match(intent, candidate, requested_name=requested_name)
    match_type = _match_type(
        intent,
        candidate,
        requested_name=requested_name,
        brand_match=brand_match,
    )
    size_or_serving_match = _size_or_serving_match(intent, candidate, title=title)
    modifier_match = _modifier_match(intent, title=title)
    source_quality_label = _source_quality_label(candidate, brand_match=brand_match)
    matched_terms = _matched_terms(
        requested_name=requested_name,
        title=title,
        brand_hint=intent.brand_hint,
        brand_detected=brand_detected,
    )
    sibling_variant_risk = _sibling_variant_risk(match_type=match_type, brand_match=brand_match)

    return {
        "packet_id": _packet_id(candidate),
        "packet_type": "SearchCandidatePacket",
        "truth_level": "candidate",
        "source_type": "web_search",
        "source_quality_label": source_quality_label,
        "officialness_hint": _text(candidate.get("officialness_hint")),
        "source_class_hint": _text(candidate.get("source_class_hint")),
        "license_status": _text(candidate.get("license_status")) or "unknown",
        "robots_status": _text(candidate.get("robots_status")) or "unknown",
        "raw_ref": _text(candidate.get("raw_ref")),
        "title": title,
        "url": url,
        "snippet": snippet,
        "tavily_score": _score(candidate.get("score")),
        "query": query,
        "matched_terms": matched_terms,
        "matched_name": requested_name,
        "canonical_name": title,
        "match_type": match_type,
        "brand_match": brand_match,
        "size_or_serving_match": size_or_serving_match,
        "modifier_match": modifier_match,
        "serving_basis": _text(candidate.get("serving_basis_candidate")) or "unknown",
        "serving_basis_candidate": _text(candidate.get("serving_basis_candidate")) or "unknown",
        "identity_confidence": _text(candidate.get("identity_confidence")) or "unknown",
        "nutrition_fields_present": list(candidate.get("nutrition_fields_present") or []),
        "sibling_variant_risk": sibling_variant_risk,
    }


def build_web_search_candidate_packets(
    intent: RetrievalIntent,
    candidates: Sequence[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    return tuple(build_web_search_candidate_packet(intent, candidate) for candidate in candidates)


def _packet_id(candidate: dict[str, object]) -> str:
    candidate_id = _text(candidate.get("candidate_id"))
    if candidate_id:
        _, _, suffix = candidate_id.rpartition(":")
        fragment = suffix or candidate_id
        return f"pkt_web_search_{fragment}"
    seed = "|".join(
        [
            _text(candidate.get("source_url")),
            _text(candidate.get("source_title")),
            _text(candidate.get("query")),
            _text(candidate.get("raw_ref")),
        ]
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"pkt_web_search_{digest}"


def _requested_identity(intent: RetrievalIntent, candidate: dict[str, object]) -> str:
    for alias in intent.aliases:
        alias_text = _text(alias)
        if alias_text:
            return alias_text
    if intent.base_dish:
        return _text(intent.base_dish)
    return _text(candidate.get("identity_target")) or _text(candidate.get("query"))


def _source_quality_label(candidate: dict[str, object], *, brand_match: str) -> str:
    officialness_hint = _text(candidate.get("officialness_hint")).lower()
    if officialness_hint == "official":
        return "brand_menu" if brand_match == "same" else "official"
    return "third_party"


def _brand_match(
    intent: RetrievalIntent,
    candidate: dict[str, object],
    *,
    requested_name: str,
) -> str:
    brand_hint = _text(intent.brand_hint)
    brand_detected = _text(candidate.get("brand_detected"))
    requested_key = lookup_key(requested_name)

    if brand_hint and brand_detected:
        if _same_text_family(brand_hint, brand_detected):
            return "same"
        return "different"
    if brand_hint:
        return "same" if lookup_key(brand_hint) and lookup_key(brand_hint) in requested_key else "unknown"
    if brand_detected:
        return "same" if lookup_key(brand_detected) and lookup_key(brand_detected) in requested_key else "unknown"
    return "unknown"


def _match_type(
    intent: RetrievalIntent,
    candidate: dict[str, object],
    *,
    requested_name: str,
    brand_match: str,
) -> str:
    if brand_match == "different":
        return "no_match"

    title = _text(candidate.get("source_title"))
    identity_confidence = _text(candidate.get("identity_confidence")).lower() or "unknown"
    requested_core = _identity_core(
        requested_name,
        brand_hint=_text(intent.brand_hint),
        size_hint=_text(intent.size_hint),
    )
    candidate_core = _identity_core(
        title,
        brand_hint=_text(candidate.get("brand_detected")) or _text(intent.brand_hint),
        size_hint="",
    )
    requested_key = lookup_key(requested_core)
    candidate_key = lookup_key(candidate_core)

    if requested_key and candidate_key and requested_key == candidate_key:
        return "exact"
    if (
        brand_match == "same"
        and requested_key
        and requested_key in candidate_key
        and not _has_unrequested_variant_token(candidate_core, requested_core)
    ):
        return "exact"

    overlap = _has_substantial_overlap(requested_core, candidate_core)
    if brand_match == "same" and overlap and identity_confidence in {"high", "medium"}:
        return "related"
    return "no_match"


def _size_or_serving_match(
    intent: RetrievalIntent,
    candidate: dict[str, object],
    *,
    title: str,
) -> str:
    requested_size = _text(intent.size_hint)
    if not requested_size:
        return "not_applicable"

    requested_group = _size_group_for_text(requested_size)
    title_group = _size_group_for_text(title)
    if requested_group and title_group:
        return "same" if requested_group == title_group else "different"
    if requested_group and _contains_any_size_alias(title):
        return "different"
    return "unknown"


def _modifier_match(intent: RetrievalIntent, *, title: str) -> str:
    if not intent.modifier_hints:
        return "not_applicable"
    title_key = lookup_key(title)
    hints = [_text(hint) for hint in intent.modifier_hints if _text(hint)]
    if hints and all(lookup_key(hint) and lookup_key(hint) in title_key for hint in hints):
        return "same"
    return "unknown"


def _matched_terms(
    *,
    requested_name: str,
    title: str,
    brand_hint: str | None,
    brand_detected: str,
) -> list[str]:
    matches: list[str] = []

    if brand_hint and brand_detected and _same_text_family(brand_hint, brand_detected):
        matches.append(normalize_text(brand_hint))

    requested_core = _identity_core(requested_name, brand_hint=brand_hint or "", size_hint="")
    candidate_core = _identity_core(title, brand_hint=brand_detected or brand_hint or "", size_hint="")
    if requested_core and lookup_key(requested_core) == lookup_key(candidate_core):
        matches.append(requested_core)
    else:
        for token in lookup_tokens(title):
            token_key = lookup_key(token)
            if token_key and token_key in lookup_key(requested_name):
                matches.append(token)
        if not matches:
            overlap = _longest_common_substring(requested_core, candidate_core)
            if len(overlap) >= 2:
                matches.append(overlap)

    deduped: list[str] = []
    for value in matches:
        cleaned = normalize_text(value)
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _sibling_variant_risk(*, match_type: str, brand_match: str) -> dict[str, object]:
    if match_type == "related" and brand_match == "same":
        return {"present": True, "reason": "same_brand_nearby_variant"}
    return {"present": False, "reason": None}


def _identity_core(text: str, *, brand_hint: str, size_hint: str) -> str:
    cleaned = normalize_text(text)
    for fragment in (brand_hint, size_hint):
        fragment_text = _text(fragment)
        if fragment_text:
            cleaned = cleaned.replace(fragment_text, " ")
    for aliases in _SIZE_ALIAS_GROUPS.values():
        for alias in aliases:
            cleaned = cleaned.replace(alias, " ")
    return normalize_text(cleaned)


def _size_group_for_text(text: str) -> str:
    haystack = normalize_text(text).lower()
    for canonical, aliases in _SIZE_ALIAS_GROUPS.items():
        if any(alias.lower() in haystack for alias in aliases):
            return canonical
    return ""


def _contains_any_size_alias(text: str) -> bool:
    return bool(_size_group_for_text(text))


def _has_substantial_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    overlap = _longest_common_substring(left, right)
    return len(overlap) >= 2


def _has_unrequested_variant_token(candidate_core: str, requested_core: str) -> bool:
    candidate_key = lookup_key(candidate_core)
    requested_key = lookup_key(requested_core)
    return any(lookup_key(token) in candidate_key and lookup_key(token) not in requested_key for token in _VARIANT_TOKENS)


def _longest_common_substring(left: str, right: str) -> str:
    if not left or not right:
        return ""
    best = ""
    left_text = normalize_text(left)
    right_text = normalize_text(right)
    for start in range(len(left_text)):
        for end in range(start + 2, len(left_text) + 1):
            fragment = left_text[start:end]
            if fragment in right_text and len(fragment) > len(best):
                best = fragment
    return best


def _same_text_family(left: str, right: str) -> bool:
    left_key = lookup_key(left)
    right_key = lookup_key(right)
    return bool(left_key and right_key and (left_key == right_key or left_key in right_key or right_key in left_key))


def _text(value: object) -> str:
    return normalize_text(value) if isinstance(value, str) else ""


def _score(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


__all__ = [
    "build_web_search_candidate_packet",
    "build_web_search_candidate_packets",
]
