from __future__ import annotations

from typing import Any

from .fooddb_retrieval_query import ALIAS_EXPANSIONS, lookup_key
from .fooddb_retrieval_records import IndexedFoodRecord

_LOCAL_ALIAS_EXPANSIONS = {
    "chicken sandwich": "\u4e09\u660e\u6cbb",
}


def _best_match(term: str, records: tuple[IndexedFoodRecord, ...]) -> dict[str, Any] | None:
    term_key = lookup_key(term)
    expansion = _alias_expansion_match(term, term_key)
    expanded_key = lookup_key(str(expansion.get("expanded") or ""))
    best: dict[str, Any] | None = None
    for record in records:
        names = (record.canonical_name, *record.aliases)
        name_keys = [lookup_key(name) for name in names]
        if term_key and term_key in name_keys:
            candidate = {
                "record": record,
                "match_path": "canonical_or_alias_exact",
                "score": 100,
                "specificity_score": len(term_key),
                "confidence": "high",
                "requires_manager_disambiguation": False,
            }
        elif term_key and any(term_key in key for key in name_keys):
            specificity = max((len(key) for key in name_keys if term_key in key), default=0)
            candidate = {
                "record": record,
                "match_path": "canonical_or_alias_substring",
                "score": 92,
                "specificity_score": specificity,
                "confidence": "medium_high",
                "requires_manager_disambiguation": True,
            }
        elif term_key and any(key and key in term_key for key in name_keys):
            specificity = max((len(key) for key in name_keys if key and key in term_key), default=0)
            candidate = {
                "record": record,
                "match_path": "query_contains_canonical_or_alias",
                "score": 90,
                "specificity_score": specificity,
                "confidence": "medium_high",
                "requires_manager_disambiguation": True,
            }
        elif expanded_key and expanded_key in name_keys:
            candidate = {
                "record": record,
                "match_path": expansion["match_path"],
                "score": expansion["score"],
                "specificity_score": len(expanded_key),
                "confidence": expansion["confidence"],
                "requires_manager_disambiguation": expansion["requires_manager_disambiguation"],
            }
        else:
            score = max((_similarity(term_key, key) for key in name_keys), default=0)
            specificity = max((len(key) for key in name_keys), default=0)
            candidate = {
                "record": record,
                "match_path": "fuzzy_alias",
                "score": score,
                "specificity_score": specificity,
                "confidence": "medium_high" if score >= 75 else "low",
                "requires_manager_disambiguation": score < 90,
            }
        if candidate["score"] < 75:
            continue
        if best is None or (
            candidate["score"],
            record.runtime_truth_allowed,
            candidate["specificity_score"],
        ) > (
            best["score"],
            best["record"].runtime_truth_allowed,
            best["specificity_score"],
        ):
            best = candidate
    return best


def _alias_expansion_match(term: str, term_key: str) -> dict[str, Any]:
    alias_expansions = {**ALIAS_EXPANSIONS, **_LOCAL_ALIAS_EXPANSIONS}
    direct = alias_expansions.get(term) or alias_expansions.get(term_key)
    if direct:
        return {
            "expanded": direct,
            "match_path": "alias_expansion_exact",
            "score": 96,
            "confidence": "high",
            "requires_manager_disambiguation": False,
        }

    best_alias: tuple[int, str] | None = None
    for alias, expanded in alias_expansions.items():
        alias_key = lookup_key(alias)
        if alias_key and alias_key in term_key:
            local_exact_alias = alias in _LOCAL_ALIAS_EXPANSIONS
            return {
                "expanded": expanded,
                "match_path": "alias_expansion_contained_in_query",
                "score": 90,
                "confidence": "medium_high",
                "requires_manager_disambiguation": not local_exact_alias,
            }
        score = _similarity(term_key, alias_key)
        if score < 85:
            continue
        if best_alias is None or score > best_alias[0]:
            best_alias = (score, expanded)
    if best_alias:
        return {
            "expanded": best_alias[1],
            "match_path": "fuzzy_alias_expansion",
            "score": best_alias[0],
            "confidence": "medium_high",
            "requires_manager_disambiguation": True,
        }
    return {
        "expanded": "",
        "match_path": "no_alias_expansion",
        "score": 0,
        "confidence": "none",
        "requires_manager_disambiguation": True,
    }


def _similarity(left: str, right: str) -> int:
    if not left or not right:
        return 0
    distance = _levenshtein(left, right)
    longest = max(len(left), len(right))
    return round((1 - distance / longest) * 100)


def _levenshtein(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (left_char != right_char)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]
