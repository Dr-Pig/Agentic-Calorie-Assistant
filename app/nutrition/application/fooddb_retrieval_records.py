from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    source_lane: str = "generic_common_serving"
    protein_g: int | None = None
    carbs_g: int | None = None
    fat_g: int | None = None
    macro_visibility_status: str = "hidden_missing_source"
    macro_source_basis: str = "unknown"
    macro_confidence: str = "unknown"



def build_runtime_retrieval_records_from_small_anchor_payload(
    payload: dict[str, Any],
) -> tuple[IndexedFoodRecord, ...]:
    return _retrieval_records(payload)


def build_runtime_retrieval_records_from_packet_ready_artifact(
    artifact: dict[str, Any],
) -> tuple[IndexedFoodRecord, ...]:
    records = []
    for item in artifact.get("packet_ready_items") or []:
        if isinstance(item, dict) and item.get("runtime_truth_allowed") is True:
            records.append(_record_from_packet_ready_item(item))
    return tuple(sorted(records, key=lambda record: record.anchor_id))


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
                    source_lane="basket_family_semantic_only",
                    runtime_truth_allowed=False,
                    runtime_role="basket_family_semantic_only",
                    kcal_point=None,
                    kcal_range=None,
                    protein_g=None,
                    carbs_g=None,
                    fat_g=None,
                    macro_visibility_status="not_applicable",
                    macro_source_basis="not_applicable",
                    macro_confidence="not_applicable",
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
                source_lane=_source_lane_from_anchor(item),
                runtime_truth_allowed=True,
                runtime_role=str(item.get("runtime_role") or ""),
                kcal_point=_optional_int(item.get("kcal_point") or item.get("baseline_likely_kcal")),
                kcal_range=_range_tuple(kcal_range),
                protein_g=None,
                carbs_g=None,
                fat_g=None,
                macro_visibility_status="hidden_missing_source",
                macro_source_basis="unknown",
                macro_confidence="unknown",
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


def _record_from_packet_ready_item(item: dict[str, Any]) -> IndexedFoodRecord:
    return IndexedFoodRecord(
        anchor_id=str(item.get("item_id") or ""),
        canonical_name=str(item.get("canonical_name") or ""),
        aliases=tuple(str(alias) for alias in item.get("aliases") or [] if str(alias).strip()),
        dish_type=str(item.get("source_lane") or ""),
        source_lane=str(item.get("source_lane") or ""),
        runtime_truth_allowed=True,
        runtime_role=str(item.get("runtime_role") or ""),
        kcal_point=_optional_int(item.get("kcal_point")),
        kcal_range=_range_tuple(item.get("kcal_range") or []),
        protein_g=_optional_int(item.get("protein_g")),
        carbs_g=_optional_int(item.get("carbs_g")),
        fat_g=_optional_int(item.get("fat_g")),
        macro_visibility_status=str(item.get("macro_visibility_status") or "unknown"),
        macro_source_basis=str(item.get("macro_source_basis") or "unknown"),
        macro_confidence=str(item.get("macro_confidence") or "unknown"),
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


def _source_lane_from_anchor(item: dict[str, Any]) -> str:
    if item.get("composition_posture") == "listed_item_component":
        return "listed_component"
    return "generic_common_serving"


def _range_tuple(values: object) -> tuple[int, int] | None:
    if not isinstance(values, list) or len(values) < 2:
        return None
    return int(values[0]), int(values[1])


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
