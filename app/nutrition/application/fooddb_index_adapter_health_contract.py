from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .fooddb_retrieval_policy import IndexedFoodRecord


@dataclass(frozen=True)
class AdapterHealthSearchCase:
    case_id: str
    query: str
    expected_top_anchor_id: str


DEFAULT_ADAPTER_HEALTH_SEARCH_CASES = (
    AdapterHealthSearchCase(
        case_id="boba_alias",
        query="boba",
        expected_top_anchor_id="custom_drink_boba_milk_tea",
    ),
    AdapterHealthSearchCase(
        case_id="chicken_bento_alias",
        query="chicken bento",
        expected_top_anchor_id="generic_meal_chicken_bento",
    ),
    AdapterHealthSearchCase(
        case_id="kelp_component",
        query="kelp",
        expected_top_anchor_id="listed_item_kelp",
    ),
    AdapterHealthSearchCase(
        case_id="latte_alias",
        query="latte",
        expected_top_anchor_id="custom_drink_latte",
    ),
)


def supabase_future_contract(
    *,
    supabase_index: FoodEvidenceIndexPort | None,
) -> dict[str, Any]:
    return {
        "status": (
            "offline_row_adapter_contract_available"
            if supabase_index is not None
            else "contract_only_not_connected"
        ),
        "runtime_dependency_allowed": False,
        "manager_visible": False,
        "required_output_contract": "IndexedFoodRecord",
        "minimum_columns": [
            "anchor_id",
            "canonical_name",
            "aliases",
            "runtime_role",
            "runtime_truth_allowed",
            "kcal_point",
            "kcal_range",
            "serving_basis",
            "portion_basis",
            "source_provenance",
            "approval_metadata",
        ],
        "forbidden_shortcuts": [
            "manager_reads_supabase_rows_directly",
            "supabase_row_becomes_runtime_truth_without_runtime_truth_allowed",
            "websearch_candidate_promotes_through_supabase_without_approval_metadata",
        ],
    }


def adapter_type(index: FoodEvidenceIndexPort) -> str:
    return str(index.describe_index().get("adapter_type") or "unknown")


def anchor_ids(records: tuple[IndexedFoodRecord, ...]) -> tuple[str, ...]:
    return tuple(record.anchor_id for record in records)


def has_text(value: object) -> bool:
    return bool(str(value or "").strip())


__all__ = [
    "AdapterHealthSearchCase",
    "DEFAULT_ADAPTER_HEALTH_SEARCH_CASES",
    "adapter_type",
    "anchor_ids",
    "has_text",
    "supabase_future_contract",
]
