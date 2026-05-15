from __future__ import annotations

from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .fooddb_index_adapter_health_contract import (
    AdapterHealthSearchCase,
    anchor_ids,
    has_text,
)
from .fooddb_retrieval_policy import IndexedFoodRecord


def record_parity_blockers(
    *,
    local_records: tuple[IndexedFoodRecord, ...],
    sqlite_records: tuple[IndexedFoodRecord, ...],
) -> list[str]:
    if local_records == sqlite_records:
        return []
    blockers = ["indexed_record_contract_drift"]
    if anchor_ids(local_records) != anchor_ids(sqlite_records):
        blockers.append("indexed_anchor_id_set_drift")
    return blockers


def record_boundary_blockers(
    *,
    label: str,
    records: tuple[IndexedFoodRecord, ...],
) -> list[str]:
    blockers: list[str] = []
    for record in records:
        prefix = f"{label}:{record.anchor_id or 'unknown_anchor'}"
        role = record.runtime_role
        if record.runtime_truth_allowed and role != "common_serving_anchor":
            blockers.append(f"{prefix}:runtime_truth_allowed_forbidden_role:{role}")
        if role == "common_serving_anchor":
            blockers.extend(_common_serving_anchor_blockers(prefix=prefix, record=record))
        elif role == "basket_family_semantic_only":
            blockers.extend(_semantic_only_blockers(prefix=prefix, record=record))
        elif role not in {
            "source_evidence_only",
            "fallback_only",
            "candidate_only",
            "websearch_candidate",
            "exact_card_candidate",
        }:
            blockers.append(f"{prefix}:unknown_runtime_role:{role}")
    return blockers


def metadata_blockers(
    *,
    local_index: FoodEvidenceIndexPort,
    sqlite_index: FoodEvidenceIndexPort,
) -> list[str]:
    blockers: list[str] = []
    local_metadata = local_index.describe_index()
    sqlite_metadata = sqlite_index.describe_index()
    if local_metadata.get("record_contract") != "IndexedFoodRecord":
        blockers.append("local_index_record_contract_mismatch")
    if sqlite_metadata.get("record_contract") != "IndexedFoodRecord":
        blockers.append("sqlite_index_record_contract_mismatch")
    if local_metadata.get("runtime_truth_boundary") != "adapter_returns_indexed_records_not_truth_decisions":
        blockers.append("local_index_runtime_truth_boundary_missing")
    if sqlite_metadata.get("runtime_truth_boundary") != "adapter_returns_indexed_records_not_truth_decisions":
        blockers.append("sqlite_index_runtime_truth_boundary_missing")
    forbidden_leaks = {"supabase_client", "webshell", "manager_context_packet"}
    for label, metadata in (("local", local_metadata), ("sqlite", sqlite_metadata)):
        forbidden = set(metadata.get("forbidden_policy_dependencies") or [])
        if not forbidden_leaks.issubset(forbidden):
            blockers.append(f"{label}_adapter_missing_forbidden_dependency_metadata")
    return blockers


def supabase_metadata_blockers(
    *,
    supabase_index: FoodEvidenceIndexPort,
) -> list[str]:
    metadata = supabase_index.describe_index()
    blockers: list[str] = []
    if metadata.get("record_contract") != "IndexedFoodRecord":
        blockers.append("supabase_index_record_contract_mismatch")
    if metadata.get("runtime_truth_boundary") != "adapter_returns_indexed_records_not_truth_decisions":
        blockers.append("supabase_index_runtime_truth_boundary_missing")
    if metadata.get("mapping_status") == "blocked":
        blockers.append("supabase_index_row_mapping_blocked")
    if int(metadata.get("mapped_record_count") or 0) <= 0:
        blockers.append("supabase_index_no_mapped_records")
    forbidden = set(metadata.get("forbidden_policy_dependencies") or [])
    if not {"supabase_client", "webshell", "manager_context_packet"}.issubset(forbidden):
        blockers.append("supabase_adapter_missing_forbidden_dependency_metadata")
    return blockers


def search_case_results(
    *,
    sqlite_index: FoodEvidenceIndexPort,
    search_cases: tuple[AdapterHealthSearchCase, ...],
) -> list[dict[str, Any]]:
    search_records = getattr(sqlite_index, "search_records", None)
    results: list[dict[str, Any]] = []
    for case in search_cases:
        records = search_records(case.query, limit=5) if callable(search_records) else ()
        top_anchor = records[0].anchor_id if records else None
        results.append(
            {
                "case_id": case.case_id,
                "query": case.query,
                "status": "pass" if top_anchor == case.expected_top_anchor_id else "fail",
                "expected_top_anchor_id": case.expected_top_anchor_id,
                "top_anchor_id": top_anchor,
                "returned_anchor_ids": [record.anchor_id for record in records],
                "runtime_mutation_allowed": False,
                "truth_selection_forbidden": True,
                "manager_visible_backend": False,
            }
        )
    return results


def search_blockers(search_results: list[dict[str, Any]]) -> list[str]:
    if all(case["status"] == "pass" for case in search_results):
        return []
    return [
        f"sqlite_fts_search_case_failed:{case['case_id']}"
        for case in search_results
        if case["status"] != "pass"
    ]


def _common_serving_anchor_blockers(*, prefix: str, record: IndexedFoodRecord) -> list[str]:
    blockers: list[str] = []
    if record.runtime_truth_allowed is not True:
        blockers.append(f"{prefix}:runtime_truth_not_allowed")
    if record.kcal_point is None:
        blockers.append(f"{prefix}:missing_kcal_point")
    if record.kcal_range is None or len(record.kcal_range) != 2:
        blockers.append(f"{prefix}:missing_kcal_range")
    if not has_text(record.serving_basis):
        blockers.append(f"{prefix}:missing_serving_basis")
    if record.portion_basis in (None, "", {}, []):
        blockers.append(f"{prefix}:missing_portion_basis")
    if not record.source_provenance:
        blockers.append(f"{prefix}:missing_source_provenance")
    if not record.approval_metadata:
        blockers.append(f"{prefix}:missing_approval_metadata")
    if not has_text(record.runtime_usage_boundary):
        blockers.append(f"{prefix}:missing_runtime_usage_boundary")
    return blockers


def _semantic_only_blockers(*, prefix: str, record: IndexedFoodRecord) -> list[str]:
    blockers: list[str] = []
    if record.runtime_truth_allowed is not False:
        blockers.append(f"{prefix}:semantic_only_runtime_truth_allowed")
    if record.kcal_point is not None or record.kcal_range is not None:
        blockers.append(f"{prefix}:semantic_only_kcal_present")
    if record.serving_basis != "not_applicable":
        blockers.append(f"{prefix}:semantic_only_serving_basis_not_applicable")
    return blockers


__all__ = [
    "metadata_blockers",
    "record_boundary_blockers",
    "record_parity_blockers",
    "search_blockers",
    "search_case_results",
    "supabase_metadata_blockers",
]
