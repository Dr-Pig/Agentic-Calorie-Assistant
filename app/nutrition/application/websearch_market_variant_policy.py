from __future__ import annotations

from .context_normalizer import lookup_key

MARKET_REGION_TOKENS = (
    "hong kong",
    "hk",
    "japan",
    "jp",
    "singapore",
    "sg",
    "taiwan",
    "tw",
)


def has_unrequested_market_token(candidate_core: str, requested_core: str) -> bool:
    candidate_key = lookup_key(candidate_core)
    requested_key = lookup_key(requested_core)
    return any(
        lookup_key(token) in candidate_key and lookup_key(token) not in requested_key
        for token in MARKET_REGION_TOKENS
    )


__all__ = ["MARKET_REGION_TOKENS", "has_unrequested_market_token"]
