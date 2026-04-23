from __future__ import annotations

from typing import Any

from .context_normalizer import has_packaged_drink_identity_cue, lookup_key


def has_explicit_exact_brand_hint(user_input: str, exact_brand_hints: list[str]) -> bool:
    user_key = lookup_key(user_input)
    if not user_key:
        return False
    for hint in exact_brand_hints:
        hint_key = lookup_key(str(hint))
        if hint_key and hint_key in user_key:
            return True
    return False


def should_soft_avoid_exact_for_generic_drink(
    *,
    user_input: str,
    standardized_drink_like: bool,
    packaged_exact_candidate_count: int,
    exact_brand_hints: list[str],
) -> bool:
    if not standardized_drink_like:
        return False
    if packaged_exact_candidate_count <= 0:
        return False
    if has_explicit_exact_brand_hint(user_input, exact_brand_hints):
        return False
    if has_packaged_drink_identity_cue(user_input):
        return False
    return True
