from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .web_search_port import WebSearchPort

_ALLOWED_CONFIDENCE = {"high", "medium", "low", "unknown"}
_ALLOWED_QUALITY_HINTS = {"high", "medium", "low", "unknown"}
_BRAND_ALIASES = {
    "starbucks": "星巴克",
}
_KNOWN_BRAND_MARKERS = (
    ("starbucks", "星巴克"),
    ("星巴克", "星巴克"),
)


async def collect_web_search_candidates(
    *,
    search_port: WebSearchPort,
    query: str,
    identity_target: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    raw_hits = await search_port.search_hits(query=query, max_results=max_results)
    return produce_web_search_candidates(
        query=query,
        identity_target=identity_target,
        raw_hits=raw_hits,
    )


def produce_web_search_candidates(
    *,
    query: str,
    identity_target: str,
    raw_hits: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, hit in enumerate(raw_hits):
        source_url = _text(hit.get("source_url") or hit.get("url"))
        source_domain = _text(hit.get("source_domain") or hit.get("domain")) or _domain_from_url(source_url)
        source_title = _text(hit.get("source_title") or hit.get("title"))
        snippet = _text(hit.get("snippet") or hit.get("content"))
        score = _number_or_none(hit.get("score"))
        source_quality_hint = _quality_hint(hit.get("source_quality_hint") or hit.get("source_quality_label"))
        officialness_hint = _officialness_hint(hit.get("officialness_hint") or hit.get("officialness"))
        raw_ref = _text(hit.get("raw_ref")) or _default_raw_ref(index=index, query=query, source_url=source_url)
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
                "brand_detected": _brand_identity(
                    _text(hit.get("brand_detected"))
                    or _infer_brand_identity(" ".join([source_title, snippet, source_domain]))
                ),
                "channel_detected": _text(hit.get("channel_detected")),
                "serving_basis_candidate": _serving_basis_candidate(
                    hit.get("serving_basis_candidate") or hit.get("serving_basis")
                ),
                "nutrition_fields_present": _string_list(hit.get("nutrition_fields_present")),
                "customization_slots_present": _string_list(hit.get("customization_slots_present")),
                "identity_confidence": _confidence(hit.get("identity_confidence")),
                "applicability_confidence": _confidence(hit.get("applicability_confidence")),
                "applicability_notes": _text(hit.get("applicability_notes")),
                "raw_ref": raw_ref,
            }
        )
    return candidates


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
    values = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return list(dict.fromkeys(values))


__all__ = [
    "collect_web_search_candidates",
    "produce_web_search_candidates",
]
