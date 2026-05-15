from __future__ import annotations

import hashlib
from itertools import islice
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .web_search_port import WebSearchPort

MAX_WEBSEARCH_RESULTS_HARD_CAP = 20
PROVIDER_TRUTH_MARKERS = frozenset(
    {
        "accepted_usage",
        "exact_card_created",
        "exactness_posture",
        "final_truth",
        "kcal_range",
        "likely_kcal",
        "mutation_allowed",
        "packet_ready_truth_allowed",
        "primary_source",
        "promotion_allowed",
        "runtime_mutation_allowed",
        "runtime_truth_allowed",
    }
)
_ALLOWED_CONFIDENCE = {"high", "medium", "low", "unknown"}
_ALLOWED_QUALITY_HINTS = {"high", "medium", "low", "unknown"}
_BRAND_ALIASES = {
    "starbucks": "星巴克",
    "matsuya": "松屋",
    "mcdonalds": "麥當勞",
    "mcdonald": "麥當勞",
    "mcdonald's": "麥當勞",
}
_KNOWN_BRAND_MARKERS = (
    ("starbucks", "星巴克"),
    ("星巴克", "星巴克"),
    ("matsuya", "松屋"),
    ("松屋", "松屋"),
    ("mcdonalds", "麥當勞"),
    ("mcdonald", "麥當勞"),
    ("麥當勞", "麥當勞"),
)


async def collect_web_search_candidates(
    *,
    search_port: WebSearchPort,
    query: str,
    identity_target: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    query_text = _text(query)
    if not query_text:
        return []
    requested_limit = bounded_websearch_max_results(max_results)
    raw_hits = await search_port.search_hits(
        query=query_text,
        max_results=requested_limit,
    )
    return produce_web_search_candidates(
        query=query_text,
        identity_target=identity_target,
        raw_hits=islice(raw_hits, requested_limit),
    )


def produce_web_search_candidates(
    *,
    query: str,
    identity_target: str,
    raw_hits: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, hit in enumerate(islice(raw_hits, MAX_WEBSEARCH_RESULTS_HARD_CAP)):
        source_url = _provider_text(hit.get("source_url") or hit.get("url"))
        source_domain = _provider_text(hit.get("source_domain") or hit.get("domain")) or _domain_from_url(source_url)
        source_title = _provider_text(hit.get("source_title") or hit.get("title"))
        snippet = _provider_text(hit.get("snippet") or hit.get("content"))
        score = _number_or_none(hit.get("score"))
        source_quality_hint = _quality_hint(
            _provider_text(hit.get("source_quality_hint") or hit.get("source_quality_label"))
        )
        officialness_hint = _officialness_hint(
            _provider_text(hit.get("officialness_hint") or hit.get("officialness"))
        )
        raw_ref = _provider_text(hit.get("raw_ref")) or _default_raw_ref(index=index, query=query, source_url=source_url)
        candidate_id = _candidate_id(query=query, source_url=source_url, source_title=source_title, index=index)
        candidates.append(
            {
                "candidate_id": candidate_id,
                "source_type": "web_search",
                "source_url": source_url,
                "source_domain": source_domain,
                "source_title": source_title,
                "snippet": snippet,
                "query": query,
                "identity_target": identity_target,
                "score": score,
                "source_quality_hint": source_quality_hint,
                "officialness_hint": officialness_hint,
                "source_class_hint": _provider_text(hit.get("source_class") or hit.get("source_class_hint")),
                "license_status": _provider_text(hit.get("license_status")) or "unknown",
                "robots_status": _provider_text(hit.get("robots_status")) or "unknown",
                "brand_detected": _brand_identity(
                    _provider_text(hit.get("brand_detected"))
                    or _infer_brand_identity(" ".join([source_title, snippet, source_domain]))
                ),
                "channel_detected": _provider_text(hit.get("channel_detected")),
                "serving_basis_candidate": _serving_basis_candidate(
                    _provider_text(hit.get("serving_basis_candidate") or hit.get("serving_basis"))
                ),
                "nutrition_fields_present": _string_list(hit.get("nutrition_fields_present")),
                "customization_slots_present": _string_list(hit.get("customization_slots_present")),
                "identity_confidence": _confidence(_provider_text(hit.get("identity_confidence"))),
                "applicability_confidence": _confidence(_provider_text(hit.get("applicability_confidence"))),
                "applicability_notes": _provider_text(hit.get("applicability_notes")),
                "raw_ref": raw_ref,
            }
        )
    return candidates


def bounded_websearch_max_results(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 5
    return max(0, min(value, MAX_WEBSEARCH_RESULTS_HARD_CAP))


def _candidate_id(*, query: str, source_url: str, source_title: str, index: int) -> str:
    digest = hashlib.sha1(f"{query}|{source_url}|{source_title}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"web_search_candidate:{digest}"


def _default_raw_ref(*, index: int, query: str, source_url: str) -> str:
    digest = hashlib.sha1(f"{query}|{source_url}|{index}".encode("utf-8")).hexdigest()[:10]
    return f"web_search_hit:{digest}"


def _domain_from_url(source_url: str) -> str:
    return urlparse(source_url).netloc.lower() if source_url else ""


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _provider_text(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    normalized = text.lower()
    return "" if any(marker in normalized for marker in PROVIDER_TRUTH_MARKERS) else text


def _brand_identity(value: str) -> str:
    return _BRAND_ALIASES.get(value.strip().lower(), value.strip())


def _infer_brand_identity(text: str) -> str:
    haystack = text.lower()
    for marker, label in _KNOWN_BRAND_MARKERS:
        if marker.lower() in haystack:
            return label
    return ""


def _number_or_none(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _quality_hint(value: object) -> str:
    hint = _text(value).lower()
    return hint if hint in _ALLOWED_QUALITY_HINTS else "unknown"


def _officialness_hint(value: object) -> str:
    hint = _text(value).lower()
    return hint or "unknown"


def _confidence(value: object) -> str:
    confidence = _text(value).lower()
    return confidence if confidence in _ALLOWED_CONFIDENCE else "unknown"


def _serving_basis_candidate(value: object) -> str:
    serving_basis = _text(value)
    return serving_basis or "unknown"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    values = [
        item
        for item in (_provider_text(raw_item) for raw_item in value)
        if item
    ]
    return list(dict.fromkeys(values))


__all__ = [
    "MAX_WEBSEARCH_RESULTS_HARD_CAP",
    "PROVIDER_TRUTH_MARKERS",
    "bounded_websearch_max_results",
    "collect_web_search_candidates",
    "produce_web_search_candidates",
]
