from __future__ import annotations

from typing import Any, Mapping


SOURCE_FAMILIES = ["fooddb", "memory", "budget", "rescue", "reusable_meal"]
CANDIDATE_FIELDS_REQUIRED = [
    "candidate_id",
    "title",
    "source_family",
    "source_refs",
]
FORBIDDEN_FIELDS = {
    "allowed_candidate_ids",
    "filtered_candidates",
    "qualified_candidates",
    "ranking_result",
    "selected_primary",
    "raw_transcript",
    "messages",
}


def build_recommendation_candidate_source_port_contract() -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_candidate_source_port_contract",
        "artifact_schema_version": "1.0",
        "source_families": list(SOURCE_FAMILIES),
        "candidate_fields_required": list(CANDIDATE_FIELDS_REQUIRED),
        "may_score_or_rank_candidates": False,
        "may_filter_hard_blockers": False,
        "canonical_product_mutation_allowed": False,
        "blockers": [],
    }


def normalize_recommendation_candidate_sources(
    *,
    payload: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    reusable_meal_context_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = _deduped(
        [
            *_fooddb_candidates(payload),
            *_memory_candidates(memory_context_pack),
            *_reusable_meal_candidates(reusable_meal_context_pack or {}),
        ]
    )
    artifact = {
        "artifact_type": "recommendation_candidate_source_port_artifact",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "source_families": list(SOURCE_FAMILIES),
        "candidate_source_ids": [
            str(candidate.get("candidate_id") or "") for candidate in candidates
        ],
        "candidate_sources": candidates,
        "source_context_views": {
            "budget": _budget_context(payload),
            "rescue": _rescue_context(payload),
        },
        "may_score_or_rank_candidates": False,
        "may_filter_hard_blockers": False,
        "canonical_product_mutation_allowed": False,
    }
    blockers = recommendation_candidate_source_port_blockers(artifact)
    return {**artifact, "status": "blocked" if blockers else "pass", "blockers": blockers}


def recommendation_candidate_source_port_blockers(
    artifact: Mapping[str, Any],
) -> list[str]:
    blockers = [
        f"candidate_source_port.forbidden_field:{field}"
        for field in sorted(FORBIDDEN_FIELDS)
        if field in artifact
    ]
    for candidate in artifact.get("candidate_sources") or []:
        if not isinstance(candidate, Mapping):
            blockers.append("candidate_source_port.candidate_not_mapping")
            continue
        missing = [
            field
            for field in CANDIDATE_FIELDS_REQUIRED
            if not candidate.get(field)
        ]
        blockers.extend(
            f"candidate_source_port.{candidate.get('candidate_id') or 'unknown'}.{field}_missing"
            for field in missing
        )
    return blockers


def _fooddb_candidates(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {**dict(candidate), "source_family": "fooddb"}
        for candidate in payload.get("candidate_source_fixture") or []
        if isinstance(candidate, Mapping)
    ]


def _memory_candidates(memory_context_pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entry in memory_context_pack.get("entries") or []:
        if not isinstance(entry, Mapping) or entry.get("memory_type") != "golden_order":
            continue
        record_id = str(entry.get("record_id") or "")
        kcal = entry.get("estimated_kcal") if isinstance(entry.get("estimated_kcal"), int) else 0
        items = [str(item) for item in entry.get("item_names") or [] if str(item)]
        title = " ".join([str(entry.get("store_name") or "Memory"), *items]).strip()
        candidates.append(
            {
                "candidate_id": record_id,
                "title": title or str(entry.get("summary") or record_id),
                "source_family": "memory",
                "source_type": "memory_golden_order",
                "estimated_kcal": kcal,
                "estimated_kcal_range": {"min": max(kcal - 80, 0), "max": kcal},
                "evidence_posture": "exact",
                "availability_posture": "available",
                "realistic_executable": True,
                "user_accessible": True,
                "item_patterns": items,
                "hard_avoid_flags": [],
                "source_refs": [f"memory_candidate:{record_id}"],
                "memory_record_id": record_id,
            }
        )
    return candidates


def _reusable_meal_candidates(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entity in context.get("reusable_meal_candidates") or []:
        if not isinstance(entity, Mapping):
            continue
        entity_id = str(entity.get("entity_id") or "")
        candidates.append(
            {
                "candidate_id": entity_id,
                "title": str(entity.get("display_name") or entity_id),
                "source_family": "reusable_meal",
                "source_type": "reusable_meal_entity",
                "source_refs": [str(ref) for ref in entity.get("source_refs") or []],
            }
        )
    return candidates


def _budget_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    budget = _mapping(payload.get("current_budget_view"))
    return {"remaining_kcal": budget.get("remaining_kcal")}


def _rescue_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    rescue = _mapping(payload.get("open_rescue_context"))
    return {
        "accepted_conflict_patterns": [
            str(item) for item in rescue.get("accepted_conflict_patterns") or []
        ]
    }


def _deduped(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if candidate_id and candidate_id not in seen:
            seen.add(candidate_id)
            deduped.append(candidate)
    return deduped


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
