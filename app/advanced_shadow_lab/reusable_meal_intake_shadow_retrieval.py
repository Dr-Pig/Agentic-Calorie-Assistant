from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.reusable_meal_memory_hint_bridge import (
    build_reusable_meal_memory_hint_bridge,
)
from app.shared.contracts.reusable_meal_policy import evaluate_reusable_meal_policy


def build_reusable_meal_intake_shadow_retrieval(
    *,
    scope_keys: Mapping[str, str],
    intake_signal: Mapping[str, Any],
    reusable_meal_entities: list[Mapping[str, Any]],
    memory_summary: Mapping[str, Any] | None = None,
    max_candidates: int = 3,
) -> dict[str, Any]:
    blockers = _scope_blockers(scope_keys)
    if blockers:
        return _artifact(status="blocked", candidates=[], omission_trace=[], blockers=blockers)

    scoped_entities: list[Mapping[str, Any]] = []
    omission_trace: list[dict[str, str]] = []
    for entity in reusable_meal_entities:
        if _entity_scope_matches(entity=entity, scope_keys=scope_keys):
            scoped_entities.append(entity)
        else:
            omission_trace.append(
                {
                    "entity_id": str(entity.get("entity_id") or ""),
                    "reason": "scope_mismatch",
                }
            )

    memory_bridge = build_reusable_meal_memory_hint_bridge(
        memory_summary=memory_summary or {},
        reusable_meal_candidate_ids=[
            str(entity.get("entity_id") or "")
            for entity in scoped_entities
            if entity.get("entity_id")
        ],
    )
    hinted_ids = set(memory_bridge["suggested_candidate_ids"])
    candidates = [
        candidate
        for candidate in (
            _candidate_from_entity(
                entity=entity,
                intake_signal=intake_signal,
                memory_hint_used=str(entity.get("entity_id") or "") in hinted_ids,
            )
            for entity in scoped_entities
        )
        if candidate is not None
    ]
    candidates.sort(key=_candidate_sort_key)
    ranked_candidates = [
        {**candidate, "retrieval_rank": index + 1}
        for index, candidate in enumerate(candidates[:max_candidates])
    ]
    return _artifact(
        status="pass",
        candidates=ranked_candidates,
        omission_trace=omission_trace,
        blockers=[],
    )


def _candidate_from_entity(
    *,
    entity: Mapping[str, Any],
    intake_signal: Mapping[str, Any],
    memory_hint_used: bool,
) -> dict[str, Any] | None:
    version = _current_version(entity)
    if not version:
        return None
    if str(version.get("normalized_signature") or "") != str(
        intake_signal.get("normalized_signature") or ""
    ):
        return None

    policy = evaluate_reusable_meal_policy(
        repetition_count=int(intake_signal.get("repetition_count") or 0),
        explicit_same_as_before=bool(intake_signal.get("explicit_same_as_before")),
        ingredient_drift=bool(intake_signal.get("ingredient_drift")),
        portion_drift=bool(intake_signal.get("portion_drift")),
        source_drift=bool(intake_signal.get("source_drift")),
        correction_count=int(entity.get("correction_count") or 0),
    )
    decision = str(policy["decision"])
    return {
        "entity_id": str(entity.get("entity_id") or ""),
        "display_name": str(entity.get("display_name") or ""),
        "current_version_id": str(entity.get("current_version_id") or ""),
        "status": str(entity.get("status") or ""),
        "review_required": entity.get("review_required") is True,
        "normalized_signature": str(version.get("normalized_signature") or ""),
        "match_basis": "normalized_signature",
        "source_kind": str(version.get("source_kind") or ""),
        "estimated_kcal": version.get("estimated_kcal") if isinstance(version.get("estimated_kcal"), int) else None,
        "estimated_kcal_range": dict(version.get("estimated_kcal_range") if isinstance(version.get("estimated_kcal_range"), Mapping) else {}),
        "source_refs": [str(ref) for ref in version.get("source_refs") or []],
        "memory_hint_used": memory_hint_used,
        "estimate_posture_decision": decision,
        "reuse_without_reestimate_allowed": decision == "reuse_exact",
        "drift_flags": dict(policy["drift_flags"]),
        "candidate_truth_owner": "reusable_meal_entity",
        "nutrition_truth_included": False,
        "canonical_mutation_requested": False,
    }


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[int, int, str]:
    hinted_score = 0 if candidate.get("memory_hint_used") is True else 1
    posture_order = {
        "reuse_exact": 0,
        "reuse_anchored": 1,
        "candidate_only": 2,
        "re_estimate_required": 3,
    }
    return (
        hinted_score,
        posture_order.get(str(candidate.get("estimate_posture_decision") or ""), 9),
        str(candidate.get("entity_id") or ""),
    )


def _current_version(entity: Mapping[str, Any]) -> Mapping[str, Any]:
    current_version_id = str(entity.get("current_version_id") or "")
    for version in entity.get("version_history") or []:
        if isinstance(version, Mapping) and str(version.get("version_id") or "") == current_version_id:
            return version
    return {}


def _entity_scope_matches(
    *,
    entity: Mapping[str, Any],
    scope_keys: Mapping[str, str],
) -> bool:
    return str(entity.get("user_id") or "") == str(scope_keys.get("user_id") or "") and str(
        entity.get("workspace_id") or ""
    ) == str(scope_keys.get("workspace_id") or "")


def _scope_blockers(scope_keys: Mapping[str, str]) -> list[str]:
    return [
        f"scope.{key}.missing"
        for key in ("user_id", "workspace_id", "surface")
        if not str(scope_keys.get(key) or "")
    ]


def _artifact(
    *,
    status: str,
    candidates: list[dict[str, Any]],
    omission_trace: list[dict[str, str]],
    blockers: list[str],
) -> dict[str, Any]:
    source_refs = [
        ref
        for candidate in candidates
        for ref in candidate["source_refs"]
    ]
    return {
        "artifact_type": "advanced_product_lab_reusable_meal_intake_shadow_retrieval",
        "artifact_schema_version": "1.0",
        "status": status,
        "typed_context_pack": {
            "reusable_meal_candidates": candidates,
            "source_refs": source_refs,
        },
        "source_ref_lookup": {
            "source_refs": source_refs,
            "source_ref_count": len(source_refs),
        },
        "retrieval_pipeline": [
            "scope_filter",
            "normalized_signature_match",
            "memory_hint_boost",
            "drift_policy",
        ],
        "omission_trace": omission_trace,
        "raw_transcript_included": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


__all__ = ["build_reusable_meal_intake_shadow_retrieval"]
