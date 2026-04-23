from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.nutrition.application.context_normalizer import canonicalize_lookup_text, lookup_key, lookup_tokens, normalize_text
from .knowledge_loader import _exact_item_cards


def _normalize(text: str) -> str:
    normalized = normalize_text(text)
    variant_map = {
        "５０嵐": "50嵐",
        "五十嵐": "50嵐",
        "７－１１": "7-11",
        "７‑１１": "7-11",
        "７―１１": "7-11",
    }
    for src, dst in variant_map.items():
        normalized = normalized.replace(src, dst)
    return normalized


def _normalize_lower(text: str) -> str:
    return _normalize(text).lower()


def _canonicalize_lookup_text(text: str) -> str:
    return canonicalize_lookup_text(_normalize(text))


def _normalize_tokens(text: str) -> list[str]:
    return lookup_tokens(_normalize(text))


def _lookup_key(text: str) -> str:
    return lookup_key(_normalize(text))


def _compact_text(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def _format_kcal_band(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    rounded = round(float(value), 1)
    if rounded.is_integer():
        return f"{int(rounded)} kcal"
    return f"{rounded} kcal"


def _parse_kcal_band_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower()
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _brand_alias_variants(brand: str) -> list[str]:
    normalized = _normalize(str(brand))
    if not normalized:
        return []
    variants = [normalized]
    replacements = {
        "50嵐": ["五十嵐", "５０嵐"],
        "五十嵐": ["50嵐", "５０嵐"],
        "7-11": ["7-ELEVEN", "7-Eleven", "７－１１"],
        "7-ELEVEN": ["7-11", "7-Eleven", "７－１１"],
        "7-Eleven": ["7-11", "7-ELEVEN", "７－１１"],
    }
    for item in replacements.get(normalized, []):
        if item not in variants:
            variants.append(item)
    return variants


def _expand_aliases(*, title: str, aliases: list[str], brand: str) -> list[str]:
    raw_aliases = [str(item).strip() for item in [title, *aliases] if str(item).strip()]
    expanded: list[str] = []
    brand_variants = _brand_alias_variants(brand)
    brand_keys = [_lookup_key(item) for item in brand_variants if _lookup_key(item)]
    for alias in raw_aliases:
        normalized = _normalize(alias)
        if not normalized:
            continue
        candidates = {
            normalized,
            re.sub(r"[()]", "", normalized).strip(),
        }
        alias_key = _lookup_key(normalized)
        for brand_variant, brand_key in zip(brand_variants, brand_keys):
            if brand_variant and brand_variant not in candidates and normalized.startswith(brand_variant):
                stripped = normalized[len(brand_variant) :].strip(" -_")
                if stripped:
                    candidates.add(stripped)
            if brand_key and alias_key.startswith(brand_key):
                stripped_key = alias_key[len(brand_key) :]
                if stripped_key:
                    candidates.add(stripped_key)
        for candidate in candidates:
            cleaned = candidate.strip()
            if cleaned and cleaned not in expanded:
                expanded.append(cleaned)
    for brand_variant in brand_variants:
        if brand_variant and brand_variant not in expanded:
            expanded.append(brand_variant)
    return expanded


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
