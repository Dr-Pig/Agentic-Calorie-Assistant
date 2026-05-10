from __future__ import annotations

from typing import Any, Mapping


def memory_action_projection_from_context(
    context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    entries = [entry for entry in context_pack.get("entries") or [] if isinstance(entry, Mapping)]
    return {
        "artifact_type": "advanced_product_lab_memory_action_projection",
        "source_context_pack_artifact_type": context_pack.get("artifact_type"),
        "negative_preference_blockers": [
            _blocker(entry) for entry in entries if entry.get("memory_type") == "negative_preference"
        ],
        "temporary_preference_blockers": [
            _blocker(entry) for entry in entries if entry.get("memory_type") == "temporary_preference"
        ],
        "interaction_suppression_blockers": [
            _interaction_suppression(entry)
            for entry in entries
            if entry.get("memory_type") == "interaction_preference"
        ],
        "raw_transcript_included": False,
        "semantic_inference_used": False,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
    }


def recommendation_memory_blocker_reasons(
    candidate: Mapping[str, Any],
    action_projection: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if _matches_any_blocker(
        candidate,
        _blockers(action_projection, "negative_preference_blockers"),
    ):
        reasons.append("memory_negative_preference_blocker")
    if _matches_any_blocker(
        candidate,
        _blockers(action_projection, "temporary_preference_blockers"),
    ):
        reasons.append("memory_temporary_preference_blocker")
    return reasons


def proactive_memory_suppression_reasons(
    *,
    trigger_type: str,
    action_projection: Mapping[str, Any],
) -> list[str]:
    for blocker in _blockers(action_projection, "interaction_suppression_blockers"):
        suppressed = {str(item) for item in blocker.get("suppressed_trigger_types") or []}
        if trigger_type in suppressed:
            return ["memory_interaction_preference_suppression"]
    return []


def _blocker(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": str(entry.get("record_id") or ""),
        "blocks_candidate_types": [
            str(item) for item in entry.get("blocks_candidate_types") or []
        ],
        "blocked_item_patterns": [
            _normalize(str(item)) for item in entry.get("blocked_item_patterns") or []
        ],
        "source_object_refs": [str(item) for item in entry.get("source_object_refs") or []],
    }


def _interaction_suppression(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": str(entry.get("record_id") or ""),
        "suppressed_trigger_types": [
            str(item) for item in entry.get("suppressed_trigger_types") or []
        ],
        "source_object_refs": [str(item) for item in entry.get("source_object_refs") or []],
    }


def _matches_any_blocker(
    candidate: Mapping[str, Any],
    blockers: list[Mapping[str, Any]],
) -> bool:
    return any(_matches_blocker(candidate, blocker) for blocker in blockers)


def _matches_blocker(
    candidate: Mapping[str, Any],
    blocker: Mapping[str, Any],
) -> bool:
    types = {str(item) for item in blocker.get("blocks_candidate_types") or []}
    if types and "recommendation_candidate" not in types:
        return False
    blocked = {str(item) for item in blocker.get("blocked_item_patterns") or []}
    if not blocked:
        return False
    patterns = {_normalize(str(item)) for item in candidate.get("item_patterns") or []}
    return bool(patterns.intersection(blocked))


def _blockers(
    projection: Mapping[str, Any],
    key: str,
) -> list[Mapping[str, Any]]:
    return [
        blocker for blocker in projection.get(key) or [] if isinstance(blocker, Mapping)
    ]


def _normalize(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


__all__ = [
    "memory_action_projection_from_context",
    "proactive_memory_suppression_reasons",
    "recommendation_memory_blocker_reasons",
]
