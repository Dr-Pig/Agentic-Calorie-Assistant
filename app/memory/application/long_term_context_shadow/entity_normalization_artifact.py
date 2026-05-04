from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import _dedupe, _slug
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _entity_normalization_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="entity_normalization_shadow_plan",
        fixture=fixture,
        extra={
            "entity_store_written": False,
            "fooddb_truth_changed": False,
            "canonical_objects_replaced": False,
            "entity_types": [
                "food_item",
                "store",
                "user_phrase",
                "preference_value",
                "conversation_topic",
            ],
            "normalization_review_lanes": [
                {
                    "lane_id": "alias_link_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
                {
                    "lane_id": "canonical_truth_conflict_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
                {
                    "lane_id": "entity_merge_split_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
            ],
            "proposed_entities": _proposed_normalized_entities(candidates),
            "source_candidate_ids": [
                candidate.candidate_id for candidate in candidates
            ],
        },
    )


def _proposed_normalized_entities(
    candidates: list[LongTermContextCandidate],
) -> list[dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}

    def add_entity(
        *,
        entity_type: str,
        label: str,
        source_candidate_id: str,
    ) -> None:
        if not label:
            return
        entity_id = f"{entity_type}-{_slug(label)}"
        entity = entities.setdefault(
            entity_id,
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "label": label,
                "source_candidate_ids": [],
                "canonical_truth_write_allowed": False,
                "runtime_effect_allowed": False,
            },
        )
        entity["source_candidate_ids"] = _dedupe(
            [*entity["source_candidate_ids"], source_candidate_id]
        )

    for candidate in candidates:
        payload = candidate.payload
        if candidate.candidate_type == "golden_order":
            add_entity(
                entity_type="store",
                label=str(payload.get("store_name") or ""),
                source_candidate_id=candidate.candidate_id,
            )
            for item in payload.get("item_names") or []:
                add_entity(
                    entity_type="food",
                    label=str(item),
                    source_candidate_id=candidate.candidate_id,
                )
        elif candidate.candidate_type == "food_preference":
            add_entity(
                entity_type="food",
                label=str(payload.get("value") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type in {
            "negative_preference",
            "temporary_preference",
        }:
            add_entity(
                entity_type="preference-value",
                label=str(payload.get("value") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type == "user_language_pattern":
            add_entity(
                entity_type="user-phrase",
                label=str(payload.get("user_phrase") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type == "conversation_recall_context":
            summaries = payload.get("conversation_summaries")
            if isinstance(summaries, list):
                for summary in summaries:
                    if not isinstance(summary, dict):
                        continue
                    for tag in summary.get("topic_tags") or []:
                        add_entity(
                            entity_type="conversation-topic",
                            label=str(tag),
                            source_candidate_id=candidate.candidate_id,
                        )

    return sorted(entities.values(), key=lambda item: item["entity_id"])
