from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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


def build_fooddb_index_adapter_health(
    *,
    local_index: FoodEvidenceIndexPort,
    sqlite_index: FoodEvidenceIndexPort,
    search_cases: tuple[AdapterHealthSearchCase, ...] = DEFAULT_ADAPTER_HEALTH_SEARCH_CASES,
) -> dict[str, Any]:
    local_records = local_index.load_records()
    sqlite_records = sqlite_index.load_records()
    search_results = _search_case_results(sqlite_index=sqlite_index, search_cases=search_cases)
    record_boundary_blockers = [
        *_record_boundary_blockers(label="local", records=local_records),
        *_record_boundary_blockers(label="sqlite", records=sqlite_records),
    ]
    metadata_blockers = _metadata_blockers(local_index=local_index, sqlite_index=sqlite_index)
    blockers = [
        *_record_parity_blockers(local_records=local_records, sqlite_records=sqlite_records),
        *record_boundary_blockers,
        *metadata_blockers,
        *_search_blockers(search_results),
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_fooddb_index_adapter_health_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_adapter_health_only",
        "claim_scope": "fooddb_index_dependency_inversion_health",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "local_record_count": len(local_records),
            "sqlite_record_count": len(sqlite_records),
            "record_contract_parity": local_records == sqlite_records,
            "local_adapter_type": _adapter_type(local_index),
            "sqlite_adapter_type": _adapter_type(sqlite_index),
            "record_boundary_passed": not record_boundary_blockers,
            "adapter_metadata_boundary_passed": not metadata_blockers,
            "runtime_boundary_passed": not record_boundary_blockers and not metadata_blockers,
            "search_case_count": len(search_results),
            "search_case_pass_count": sum(1 for case in search_results if case["status"] == "pass"),
            "search_case_fail_count": sum(1 for case in search_results if case["status"] != "pass"),
        },
        "dependency_inversion": {
            "stable_application_contract": "FoodEvidenceIndexPort.load_records -> IndexedFoodRecord",
            "search_contract_status": "adapter_owned_optional_capability",
            "retrieval_policy_forbidden_dependencies": [
                "sqlite_db_path",
                "supabase_client",
                "websearch_client",
                "webshell",
                "manager_context_packet",
            ],
            "manager_visible_backend": False,
            "packetizer_format_changed": False,
        },
        "adapter_metadata": {
            "local": local_index.describe_index(),
            "sqlite_fts": sqlite_index.describe_index(),
        },
        "search_cases": search_results,
        "future_backend_contracts": {
            "supabase": _supabase_future_contract(),
        },
        "next_required_slice": (
            "grokfast_fooddb_diagnostic_preflight"
            if clear
            else "inspect_fooddb_index_adapter_health_blockers"
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_supabase_connection",
            "no_readiness_claim",
        ],
    }


def _record_parity_blockers(
    *,
    local_records: tuple[IndexedFoodRecord, ...],
    sqlite_records: tuple[IndexedFoodRecord, ...],
) -> list[str]:
    if local_records == sqlite_records:
        return []
    blockers = ["indexed_record_contract_drift"]
    if _anchor_ids(local_records) != _anchor_ids(sqlite_records):
        blockers.append("indexed_anchor_id_set_drift")
    return blockers


def _record_boundary_blockers(
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


def _common_serving_anchor_blockers(*, prefix: str, record: IndexedFoodRecord) -> list[str]:
    blockers: list[str] = []
    if record.runtime_truth_allowed is not True:
        blockers.append(f"{prefix}:runtime_truth_not_allowed")
    if record.kcal_point is None:
        blockers.append(f"{prefix}:missing_kcal_point")
    if record.kcal_range is None or len(record.kcal_range) != 2:
        blockers.append(f"{prefix}:missing_kcal_range")
    if not _has_text(record.serving_basis):
        blockers.append(f"{prefix}:missing_serving_basis")
    if record.portion_basis in (None, "", {}, []):
        blockers.append(f"{prefix}:missing_portion_basis")
    if not record.source_provenance:
        blockers.append(f"{prefix}:missing_source_provenance")
    if not record.approval_metadata:
        blockers.append(f"{prefix}:missing_approval_metadata")
    if not _has_text(record.runtime_usage_boundary):
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


def _metadata_blockers(
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


def _search_case_results(
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


def _search_blockers(search_results: list[dict[str, Any]]) -> list[str]:
    if all(case["status"] == "pass" for case in search_results):
        return []
    return [
        f"sqlite_fts_search_case_failed:{case['case_id']}"
        for case in search_results
        if case["status"] != "pass"
    ]


def _supabase_future_contract() -> dict[str, Any]:
    return {
        "status": "contract_only_not_connected",
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


def _adapter_type(index: FoodEvidenceIndexPort) -> str:
    return str(index.describe_index().get("adapter_type") or "unknown")


def _anchor_ids(records: tuple[IndexedFoodRecord, ...]) -> tuple[str, ...]:
    return tuple(record.anchor_id for record in records)


def _has_text(value: object) -> bool:
    return bool(str(value or "").strip())


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "AdapterHealthSearchCase",
    "DEFAULT_ADAPTER_HEALTH_SEARCH_CASES",
    "build_fooddb_index_adapter_health",
]
