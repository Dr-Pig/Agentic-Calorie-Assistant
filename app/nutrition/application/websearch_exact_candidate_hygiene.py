from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


FORBIDDEN_LEAKAGE_MARKERS = (
    "candidate_packet",
    "likely_kcal",
    "observed_manager_output",
    "provider_trace",
    "raw_response_excerpt",
    "runtime_truth_allowed",
)

ALLOWED_SERVING_BASIS_CANDIDATES = {
    "per_bottle",
    "per_bowl",
    "per_box",
    "per_can",
    "per_cup",
    "per_item",
    "per_package",
    "per_piece",
    "per_plate",
    "per_portion",
    "per_serving",
    "per_slice",
    "per_wrap",
}


def contains_leakage_marker(value: Any) -> bool:
    text = str(value or "").lower()
    return any(marker in text for marker in FORBIDDEN_LEAKAGE_MARKERS)


def safe_https_url(value: Any) -> bool:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return bool(
        parsed.scheme == "https"
        and parsed.netloc
        and parsed.path
        and not _contains_private_token_pattern(text)
        and not contains_leakage_marker(text)
    )


def safe_display_text(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not contains_leakage_marker(text)


def safe_serving_basis_candidate(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in ALLOWED_SERVING_BASIS_CANDIDATES and not contains_leakage_marker(text)


def _contains_private_token_pattern(value: str) -> bool:
    text = value.lower()
    return "private" in text and ("payload" in text or "token" in text)


__all__ = [
    "ALLOWED_SERVING_BASIS_CANDIDATES",
    "contains_leakage_marker",
    "safe_display_text",
    "safe_https_url",
    "safe_serving_basis_candidate",
]
