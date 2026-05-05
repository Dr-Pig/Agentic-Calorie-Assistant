from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
import unicodedata
from typing import Any


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

MODIFIER_VALUE_EQUIVALENTS = {
    "rice_portion": {
        "less_rice": {"half", "small"},
        "half_rice": {"half", "small"},
    },
}


@dataclass(frozen=True)
class IndexedFoodRecord:
    anchor_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    dish_type: str
    runtime_truth_allowed: bool
    runtime_role: str
    kcal_point: int | None
    kcal_range: tuple[int, int] | None
    serving_basis: str
    portion_basis: Any
    followup_hints: tuple[str, ...]
    major_modifiers: tuple[dict[str, Any], ...]
    runtime_usage_boundary: str
    source_provenance: dict[str, Any]
    approval_metadata: dict[str, Any]


def retrieve_fooddb_candidates(
    query: str,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    limit: int = 5,
) -> dict[str, Any]:
    normalized = _normalized_query(query)
    candidate_terms = _candidate_query_terms(normalized)
    normalized = {**normalized, "candidate_terms": candidate_terms}
    semantic_basket = _bare_basket_match(normalized["lookup_key"], retrieval_records)
    listed_components = _listed_basket_components(normalized["normalized_text"])

    if semantic_basket and not listed_components:
        return _result(
            normalized_query=normalized,
            accepted=[],
            rejected=[],
            retrieval_boundary="bare_basket_ask_followup_no_estimate",
            followup_hints=semantic_basket,
        )

    if listed_components:
        component_candidates = []
        rejected = []
        for component in listed_components:
            match = _best_match(component, retrieval_records)
            if match is None:
                rejected.append(
                    {
                        "query_component": component,
                        "reason": "no_runtime_anchor_match",
                    }
                )
                continue
            component_candidates.append(
                _candidate_payload(
                    match,
                    query_component=component,
                    modifier_hints=normalized["modifier_hints"],
                )
            )
        component_candidates.sort(key=lambda item: str(item["anchor_id"]))
        return _result(
            normalized_query=normalized,
            accepted=component_candidates[:limit],
            rejected=rejected,
            retrieval_boundary="listed_basket_component_recall",
            followup_hints=[],
        )

    candidates = []
    rejected = []
    for term in candidate_terms:
        match = _best_match(term, retrieval_records)
        if match is None:
            rejected.append({"query_term": term, "reason": "no_runtime_anchor_match"})
            continue
        payload = _candidate_payload(
            match,
            query_component=term,
            modifier_hints=normalized["modifier_hints"],
        )
        if payload not in candidates:
            candidates.append(payload)
    candidates = _rank_candidates(candidates)[:limit]

    return _result(
        normalized_query=normalized,
        accepted=candidates,
        rejected=rejected[:limit],
        retrieval_boundary="single_or_composite_candidate_recall",
        followup_hints=[],
    )


def build_fooddb_retrieval_policy_artifact(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    runtime_anchor_records = [
        record for record in retrieval_records if record.runtime_role == "common_serving_anchor"
    ]
    semantic_basket_records = [
        record for record in retrieval_records if record.runtime_role == "basket_family_semantic_only"
    ]
    return {
        "artifact_type": "accurate_intake_fooddb_retrieval_policy",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_retrieval_policy_report_only",
        "runtime_truth_changed": False,
        "product_loop_integration_claimed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "retrieval_architecture": {
            "dependency_inversion": {
                "policy_layer_depends_on": "FoodDB evidence records supplied by adapter",
                "forbidden_dependencies": [
                    "sqlite_file_path",
                    "supabase_client",
                    "webshell",
                    "manager_context_packet",
                ],
                "future_adapter_shape": "local_json_or_sqlite_or_supabase_can_supply_same_records",
            },
            "stages": [
                "text_normalization",
                "exact_alias_lookup",
                "alias_expansion_lookup",
                "fuzzy_lexical_lookup",
                "basket_family_component_parse",
                "deterministic_candidate_ranking",
                "manager_disambiguation_later",
            ],
            "vector_search_policy": _vector_search_policy(),
        },
        "summary": {
            "runtime_anchor_indexed_count": len(runtime_anchor_records),
            "semantic_basket_indexed_count": len(semantic_basket_records),
            "alias_expansion_count": len(ALIAS_EXPANSIONS),
            "basket_family_count": len(BASKET_TERMS),
        },
        "manager_retrieval_catalog": {
            "claim_scope": "compact_runtime_retrieval_catalog_not_raw_database",
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
            "anchors": [
                {
                    "anchor_id": record.anchor_id,
                    "canonical_name": record.canonical_name,
                    "aliases": list(record.aliases),
                    "dish_type": record.dish_type,
                    "runtime_usage_boundary": record.runtime_usage_boundary,
                }
                for record in retrieval_records
            ],
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_vector_truth_selection",
        ],
    }


def build_runtime_retrieval_records_from_small_anchor_payload(
    payload: dict[str, Any],
) -> tuple[IndexedFoodRecord, ...]:
    return _retrieval_records(payload)


def _result(
    *,
    normalized_query: dict[str, Any],
    accepted: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    retrieval_boundary: str,
    followup_hints: list[str],
) -> dict[str, Any]:
    return {
        "retrieval_scope": "candidate_recall_only",
        "truth_selection_forbidden": True,
        "runtime_mutation_allowed": False,
        "retrieval_boundary": retrieval_boundary,
        "normalized_query": normalized_query,
        "accepted_candidates": accepted,
        "rejected_candidates": rejected,
        "ambiguity_reason": _ambiguity_reason(accepted),
        "followup_hints": followup_hints,
        "vector_search_policy": _vector_search_policy(),
        "ranking_policy": _ranking_policy(),
    }


def _retrieval_records(payload: dict[str, Any]) -> tuple[IndexedFoodRecord, ...]:
    records = []
    for item in payload.get("anchors") or []:
        if not isinstance(item, dict):
            continue
        if item.get("record_kind") == "generic_semantic_only":
            records.append(
                IndexedFoodRecord(
                    anchor_id=str(item.get("anchor_id") or item.get("canonical_name") or ""),
                    canonical_name=str(item.get("canonical_name") or ""),
                    aliases=tuple(str(alias) for alias in item.get("aliases") or [] if str(alias).strip()),
                    dish_type=str(item.get("dish_type") or ""),
                    runtime_truth_allowed=False,
                    runtime_role="basket_family_semantic_only",
                    kcal_point=None,
                    kcal_range=None,
                    serving_basis="not_applicable",
                    portion_basis="not_applicable",
                    followup_hints=tuple(
                        str(hint) for hint in item.get("followup_hints") or [] if str(hint).strip()
                    ),
                    major_modifiers=(),
                    runtime_usage_boundary="bare_basket_ask_followup_no_estimate",
                    source_provenance={},
                    approval_metadata={},
                )
            )
            continue
        if item.get("record_kind") != "generic_anchor":
            continue
        if item.get("runtime_role") != "common_serving_anchor":
            continue
        if item.get("runtime_truth_allowed") is not True:
            continue
        kcal_range = item.get("kcal_range") or item.get("baseline_kcal_range") or []
        records.append(
            IndexedFoodRecord(
                anchor_id=str(item.get("anchor_id") or ""),
                canonical_name=str(item.get("canonical_name") or ""),
                aliases=tuple(str(alias) for alias in item.get("aliases") or [] if str(alias).strip()),
                dish_type=str(item.get("dish_type") or ""),
                runtime_truth_allowed=True,
                runtime_role=str(item.get("runtime_role") or ""),
                kcal_point=_optional_int(item.get("kcal_point") or item.get("baseline_likely_kcal")),
                kcal_range=_range_tuple(kcal_range),
                serving_basis=str(item.get("serving_basis") or ""),
                portion_basis=item.get("portion_basis") or "",
                followup_hints=tuple(str(hint) for hint in item.get("followup_hints") or [] if str(hint).strip()),
                major_modifiers=tuple(
                    modifier for modifier in item.get("major_modifiers") or [] if isinstance(modifier, dict)
                ),
                runtime_usage_boundary=str(item.get("runtime_usage_boundary") or ""),
                source_provenance=dict(item.get("source_provenance") or {}),
                approval_metadata=dict(item.get("approval_metadata") or {}),
            )
        )
    return tuple(sorted(records, key=lambda record: record.anchor_id))


def _best_match(term: str, records: tuple[IndexedFoodRecord, ...]) -> dict[str, Any] | None:
    term_key = _lookup_key(term)
    expansion = _alias_expansion_match(term, term_key)
    expanded_key = _lookup_key(str(expansion.get("expanded") or ""))
    best: dict[str, Any] | None = None
    for record in records:
        names = (record.canonical_name, *record.aliases)
        name_keys = [_lookup_key(name) for name in names]
        if term_key and term_key in name_keys:
            candidate = {
                "record": record,
                "match_path": "canonical_or_alias_exact",
                "score": 100,
                "confidence": "high",
                "requires_manager_disambiguation": False,
            }
        elif expanded_key and expanded_key in name_keys:
            candidate = {
                "record": record,
                "match_path": expansion["match_path"],
                "score": expansion["score"],
                "confidence": expansion["confidence"],
                "requires_manager_disambiguation": expansion["requires_manager_disambiguation"],
            }
        else:
            score = max((_similarity(term_key, key) for key in name_keys), default=0)
            candidate = {
                "record": record,
                "match_path": "fuzzy_alias",
                "score": score,
                "confidence": "medium_high" if score >= 75 else "low",
                "requires_manager_disambiguation": score < 90,
            }
        if candidate["score"] < 75:
            continue
        if best is None or (candidate["score"], record.runtime_truth_allowed) > (
            best["score"],
            best["record"].runtime_truth_allowed,
        ):
            best = candidate
    return best


def _candidate_payload(
    match: dict[str, Any],
    *,
    query_component: str,
    modifier_hints: dict[str, str],
) -> dict[str, Any]:
    record: IndexedFoodRecord = match["record"]
    modifier_compatibility = _modifier_compatibility(record, modifier_hints)
    return {
        "anchor_id": record.anchor_id,
        "canonical_name": record.canonical_name,
        "query_component": query_component,
        "match_path": match["match_path"],
        "match_score": match["score"],
        "confidence": match["confidence"],
        "requires_manager_disambiguation": match["requires_manager_disambiguation"],
        "runtime_truth_allowed": record.runtime_truth_allowed,
        "runtime_role": record.runtime_role,
        "kcal_point": record.kcal_point,
        "kcal_range": list(record.kcal_range) if record.kcal_range else None,
        "serving_basis": record.serving_basis,
        "portion_basis": record.portion_basis,
        "runtime_usage_boundary": record.runtime_usage_boundary,
        "followup_hints": list(record.followup_hints),
        "source_provenance": record.source_provenance,
        "approval_metadata": record.approval_metadata,
        "modifier_compatibility": modifier_compatibility,
        "ranking_reasons": _ranking_reasons(
            match,
            record=record,
            modifier_compatibility=modifier_compatibility,
        ),
    }


def _alias_expansion_match(term: str, term_key: str) -> dict[str, Any]:
    direct = ALIAS_EXPANSIONS.get(term) or ALIAS_EXPANSIONS.get(term_key)
    if direct:
        return {
            "expanded": direct,
            "match_path": "alias_expansion_exact",
            "score": 96,
            "confidence": "high",
            "requires_manager_disambiguation": False,
        }

    best_alias: tuple[int, str] | None = None
    for alias, expanded in ALIAS_EXPANSIONS.items():
        score = _similarity(term_key, _lookup_key(alias))
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


def _modifier_compatibility(
    record: IndexedFoodRecord,
    modifier_hints: dict[str, str],
) -> dict[str, str]:
    compatibility: dict[str, str] = {}
    modifier_values = {
        str(modifier.get("name") or ""): {str(value) for value in modifier.get("values") or []}
        for modifier in record.major_modifiers
        if isinstance(modifier, dict)
    }
    for modifier_name, modifier_value in modifier_hints.items():
        supported_values = modifier_values.get(modifier_name)
        equivalent_values = MODIFIER_VALUE_EQUIVALENTS.get(modifier_name, {}).get(
            modifier_value,
            set(),
        )
        if supported_values and modifier_value in supported_values:
            compatibility[modifier_name] = "compatible"
        elif supported_values and bool(equivalent_values & supported_values):
            compatibility[modifier_name] = "compatible_via_normalized_equivalent"
        else:
            compatibility[modifier_name] = "unsupported"
    return compatibility


def _ranking_reasons(
    match: dict[str, Any],
    *,
    record: IndexedFoodRecord,
    modifier_compatibility: dict[str, str],
) -> list[str]:
    reasons = [str(match["match_path"])]
    if record.runtime_truth_allowed:
        reasons.append("runtime_truth_allowed")
    if record.kcal_range:
        reasons.append("kcal_range_present")
    if record.serving_basis and record.serving_basis != "not_applicable":
        reasons.append("serving_basis_present")
    if record.portion_basis and record.portion_basis != "not_applicable":
        reasons.append("portion_basis_present")
    for modifier_name, status in modifier_compatibility.items():
        if status == "compatible":
            reasons.append(f"modifier_compatible:{modifier_name}")
    return reasons


def _candidate_query_terms(normalized: dict[str, Any]) -> list[str]:
    text = normalized["normalized_text"]
    terms = [text]
    compact = _strip_known_modifier_terms(text)
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


def _listed_basket_components(text: str) -> list[str]:
    if not any(term in text for term in BASKET_TERMS):
        return []
    if not any(marker in text for marker in ("有", "、", ",", "，")):
        return []
    tail = text
    for marker in ("有", "吃了", "買了"):
        if marker in tail:
            tail = tail.split(marker, 1)[1]
    for term in BASKET_TERMS:
        tail = tail.replace(term, "")
    parts = [part.strip(" 的，,。 ") for part in re.split(r"[、,，和與]", tail)]
    return [part for part in parts if part]


def _bare_basket_match(
    lookup_key: str,
    records: tuple[IndexedFoodRecord, ...],
) -> list[str] | None:
    for record in records:
        if record.runtime_role != "basket_family_semantic_only":
            continue
        names = [record.canonical_name, *record.aliases]
        if any(_lookup_key(name) and _lookup_key(name) in lookup_key for name in names):
            return list(record.followup_hints or ("請列出籃子食物的品項",))
    return None


def _normalized_query(query: str) -> dict[str, Any]:
    text = unicodedata.normalize("NFKC", query or "").strip()
    return {
        "raw_text": query,
        "normalized_text": text,
        "lookup_key": _lookup_key(text),
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


def _rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int, int, str]:
        path_rank = {
            "canonical_or_alias_exact": 0,
            "alias_expansion_exact": 1,
            "fuzzy_alias_expansion": 2,
            "fuzzy_alias": 3,
        }.get(str(item.get("match_path")), 9)
        modifier_compatibility = item.get("modifier_compatibility") or {}
        if not isinstance(modifier_compatibility, dict):
            modifier_compatibility = {}
        unsupported_modifier_count = sum(
            1 for status in modifier_compatibility.values() if status == "unsupported"
        )
        compatible_modifier_count = sum(
            1 for status in modifier_compatibility.values() if status == "compatible"
        )
        source_quality_score = 1 if item.get("source_provenance") else 0
        runtime_truth_score = 1 if item.get("runtime_truth_allowed") is True else 0
        serving_basis_score = 1 if item.get("serving_basis") else 0
        portion_basis_score = 1 if item.get("portion_basis") else 0
        ambiguity_penalty = 1 if item.get("requires_manager_disambiguation") else 0
        return (
            path_rank,
            unsupported_modifier_count,
            -compatible_modifier_count,
            -runtime_truth_score,
            -source_quality_score,
            -serving_basis_score,
            -portion_basis_score,
            -int(item.get("match_score") or 0),
            ambiguity_penalty,
            str(item.get("anchor_id") or ""),
        )

    return sorted(candidates, key=key)


def _ambiguity_reason(accepted: list[dict[str, Any]]) -> str | None:
    if len(accepted) <= 1:
        return None
    return "multiple_retrieval_candidates_require_manager_disambiguation"


def _lookup_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized))


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


def _range_tuple(values: object) -> tuple[int, int] | None:
    if not isinstance(values, list) or len(values) < 2:
        return None
    return int(values[0]), int(values[1])


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _vector_search_policy() -> dict[str, Any]:
    return {
        "allowed_for": "candidate_recall_later_only",
        "forbidden_for": [
            "truth_selection",
            "kcal_decision",
            "runtime_mutation",
        ],
    }


def _ranking_policy() -> dict[str, Any]:
    return {
        "features": [
            "lexical_match",
            "runtime_truth_allowed",
            "source_quality",
            "serving_basis",
            "portion_basis",
            "modifier_compatibility",
            "ambiguity_risk",
        ],
        "truth_selection": "forbidden",
        "manager_role": "disambiguate_or_synthesize_from_candidates",
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "IndexedFoodRecord",
    "build_fooddb_retrieval_policy_artifact",
    "build_runtime_retrieval_records_from_small_anchor_payload",
    "retrieve_fooddb_candidates",
]
