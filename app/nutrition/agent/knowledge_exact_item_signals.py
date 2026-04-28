from __future__ import annotations

from functools import lru_cache

from .knowledge_loader import _exact_item_cards
from .knowledge_lookup_normalizer import _lookup_key, _normalize_tokens


@lru_cache(maxsize=1)
def _exact_item_signal_tokens() -> set[str]:
    tokens: set[str] = set()
    for card in _exact_item_cards():
        for field in (
            str(card.get("brand", "")),
            str(card.get("title", "")),
            *[str(item) for item in card.get("aliases", []) if isinstance(item, str)],
        ):
            tokens.update(_normalize_tokens(field))
    return tokens


@lru_cache(maxsize=1)
def _exact_item_brand_keys() -> set[str]:
    keys: set[str] = set()
    for card in _exact_item_cards():
        brand = _lookup_key(str(card.get("brand", "")))
        if brand:
            keys.add(brand)
    return keys
