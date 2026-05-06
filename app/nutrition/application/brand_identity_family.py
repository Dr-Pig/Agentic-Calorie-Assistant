from __future__ import annotations

from .context_normalizer import lookup_key

_BRAND_FAMILIES: tuple[tuple[str, ...], ...] = (
    ("starbucks", "\u661f\u5df4\u514b"),
    ("milksha", "\u8ff7\u5ba2\u590f"),
)


def same_brand_family(left: str, right: str) -> bool:
    left_key = _brand_family_key(left)
    right_key = _brand_family_key(right)
    return bool(left_key and right_key and left_key == right_key)


def _brand_family_key(value: str) -> str:
    text_key = lookup_key(value)
    if not text_key:
        return ""
    for family in _BRAND_FAMILIES:
        if any(lookup_key(alias) == text_key for alias in family):
            return lookup_key(family[0])
    return text_key


def brand_identity_variants(value: str) -> tuple[str, ...]:
    text_key = lookup_key(value)
    if not text_key:
        return ()
    for family in _BRAND_FAMILIES:
        if any(lookup_key(alias) == text_key for alias in family):
            return family
    return (value,)


__all__ = ["brand_identity_variants", "same_brand_family"]
