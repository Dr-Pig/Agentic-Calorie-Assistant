from __future__ import annotations

from .context_normalizer import normalize_text

SIZE_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "\u7279\u76db": ("\u7279\u76db",),
    "\u5927\u676f": ("\u5927\u676f", "large", "venti"),
    "\u4e2d\u676f": ("\u4e2d\u676f", "medium", "grande"),
    "\u5c0f\u676f": ("\u5c0f\u676f", "small", "tall"),
}

VARIANT_TOKENS = ("抹茶", "摩卡", "可可", "焦糖", "香草", "榛果", "醇濃")

IDENTITY_ALIAS_EQUIVALENTS = {
    "那堤": "拿鐵",
    "拿鉄": "拿鐵",
    "拿铁": "拿鐵",
}


def normalize_identity_aliases(text: str) -> str:
    cleaned = text
    for source, canonical in IDENTITY_ALIAS_EQUIVALENTS.items():
        cleaned = cleaned.replace(source, canonical)
    return cleaned


def size_or_serving_match(size_hint: str | None, *, title: str, snippet: str) -> str:
    requested_size = normalize_text(size_hint) if isinstance(size_hint, str) else ""
    if not requested_size:
        return "not_applicable"

    requested_group = _size_group_for_text(requested_size)
    title_group = _size_group_for_text(title)
    if requested_group and title_group:
        return "same" if requested_group == title_group else "different"
    if requested_group and _contains_any_size_alias(title):
        return "different"
    snippet_group = _size_group_for_text(snippet)
    if requested_group and snippet_group:
        return "same" if requested_group == snippet_group else "different"
    if requested_group and _contains_any_size_alias(snippet):
        return "different"
    return "unknown"


def _size_group_for_text(text: str) -> str:
    haystack = normalize_text(text).lower()
    for canonical, aliases in SIZE_ALIAS_GROUPS.items():
        if any(alias.lower() in haystack for alias in aliases):
            return canonical
    return ""


def _contains_any_size_alias(text: str) -> bool:
    return bool(_size_group_for_text(text))


__all__ = [
    "IDENTITY_ALIAS_EQUIVALENTS",
    "SIZE_ALIAS_GROUPS",
    "VARIANT_TOKENS",
    "normalize_identity_aliases",
    "size_or_serving_match",
]
