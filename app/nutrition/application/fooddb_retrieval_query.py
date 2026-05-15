from __future__ import annotations

import re
import unicodedata
from typing import Any

from .fooddb_retrieval_records import IndexedFoodRecord

ALIAS_EXPANSIONS = {
    "珍奶": "珍珠奶茶",
    "波霸奶茶": "珍珠奶茶",
    "boba": "珍珠奶茶",
    "boba milk tea": "珍珠奶茶",
    "拿鉄": "拿鐵",
    "拿铁": "拿鐵",
}

BASKET_TERMS = {
    "滷味",
    "麻辣燙",
    "鹽酥雞",
    "關東煮",
}

MODIFIER_PATTERNS = {
    "cup_size": {
        "大杯": "large",
        "中杯": "medium",
        "小杯": "small",
        "large": "large",
        "medium": "medium",
        "small": "small",
    },
    "sugar_level": {
        "無糖": "unsweetened",
        "半糖": "half_sugar",
        "全糖": "full_sugar",
        "少糖": "low_sugar",
    },
    "rice_portion": {
        "少飯": "less_rice",
        "飯少一點": "less_rice",
        "半飯": "half_rice",
        "飯半碗": "half_rice",
        "飯少": "less_rice",
    },
}

_QUERY_WRAPPER_TERMS = (
    "\u65e9\u9910",
    "\u5348\u9910",
    "\u665a\u9910",
    "\u5bb5\u591c",
    "\u5403\u4e86",
    "\u5403",
    "\u559d\u4e86",
    "\u559d",
    "\u4e00\u7897",
    "\u4e00\u4efd",
    "\u4e00\u76e4",
    "\u4e00\u500b",
)


def _candidate_query_terms(normalized: dict[str, Any]) -> list[str]:
    text = normalized["normalized_text"]
    terms = [text]
    compact = _strip_known_modifier_terms(text)
    compact = _strip_query_wrapper_terms(compact)
    compact = re.sub(r"(我|吃了|喝了|一杯|一份|一個|一顆|大杯|中杯|小杯|半糖|無糖|全糖)", "", compact)
    compact = compact.strip(" ，,。")
    if compact and compact not in terms:
        terms.append(compact)
    return [term for term in terms if term]


def _strip_known_modifier_terms(text: str) -> str:
    compact = text
    for patterns in MODIFIER_PATTERNS.values():
        for pattern in patterns:
            if pattern:
                compact = compact.replace(pattern, "")
    return compact


def _strip_query_wrapper_terms(text: str) -> str:
    compact = text
    for term in _QUERY_WRAPPER_TERMS:
        compact = compact.replace(term, "")
    return compact


def _listed_basket_components(text: str) -> list[str]:
    if not any(term in text for term in BASKET_TERMS):
        return []
    if not any(marker in text for marker in (" ", "有", "、", ",", "，")):
        return []
    tail = text
    for marker in ("有", "吃了", "買了"):
        if marker in tail:
            tail = tail.split(marker, 1)[1]
    for term in BASKET_TERMS:
        tail = tail.replace(term, "")
    parts = [part.strip(" 的，,。 ") for part in re.split(r"[\s、,，和與]", tail)]
    return [part for part in parts if part]


def _bare_basket_match(
    query_lookup_key: str,
    records: tuple[IndexedFoodRecord, ...],
) -> list[str] | None:
    for record in records:
        if record.runtime_role != "basket_family_semantic_only":
            continue
        names = [record.canonical_name, *record.aliases]
        if any(lookup_key(name) and lookup_key(name) in query_lookup_key for name in names):
            return list(record.followup_hints or ("請列出籃子食物的品項",))
    return None


def _normalized_query(query: str) -> dict[str, Any]:
    text = unicodedata.normalize("NFKC", query or "").strip()
    return {
        "raw_text": query,
        "normalized_text": text,
        "lookup_key": lookup_key(text),
        "modifier_hints": _modifier_hints(text),
    }


def _modifier_hints(text: str) -> dict[str, str]:
    hints = {}
    for modifier_name, patterns in MODIFIER_PATTERNS.items():
        for pattern, normalized_value in patterns.items():
            if pattern in text:
                hints[modifier_name] = normalized_value
                break
    return hints


def lookup_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized))
