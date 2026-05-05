from __future__ import annotations

SIZE_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "\u7279\u76db": ("\u7279\u76db",),
    "\u5927\u676f": ("\u5927\u676f", "large", "venti"),
    "\u4e2d\u676f": ("\u4e2d\u676f", "medium", "grande"),
    "\u5c0f\u676f": ("\u5c0f\u676f", "small", "tall"),
}

VARIANT_TOKENS = ("抹茶", "摩卡", "可可", "焦糖", "香草", "榛果", "醇濃")

__all__ = [
    "SIZE_ALIAS_GROUPS",
    "VARIANT_TOKENS",
]
