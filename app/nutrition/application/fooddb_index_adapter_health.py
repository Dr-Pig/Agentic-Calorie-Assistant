from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .fooddb_index_adapter_health_checks import (
    metadata_blockers,
    record_boundary_blockers,
    record_parity_blockers,
    search_blockers,
    search_case_results,
    supabase_metadata_blockers,
)
from .fooddb_index_adapter_health_contract import (
    DEFAULT_ADAPTER_HEALTH_SEARCH_CASES,
    AdapterHealthSearchCase,
    adapter_type,
    supabase_future_contract,
)


def build_fooddb_index_adapter_health(
    *,
    local_index: FoodEvidenceIndexPort,
    sqlite_index: FoodEvidenceIndexPort,
    supabase_index: FoodEvidenceIndexPort | None = None,
    search_cases: tuple[AdapterHealthSearchCase, ...] = DEFAULT_ADAPTER_HEALTH_SEARCH_CASES,
) -> dict[str, Any]:
    local_records = local_index.load_records()
    sqlite_records = sqlite_index.load_records()
    supabase_records = supabase_index.load_records() if supabase_index is not None else ()
    search_results = search_case_results(sqlite_index=sqlite_index, search_cases=search_cases)
    record_boundary_findings = [
        *record_boundary_blockers(label="local", records=local_records),
        *record_boundary_blockers(label="sqlite", records=sqlite_records),
        *(
            record_boundary_blockers(label="supabase", records=supabase_records)
            if supabase_index is not None
            else []
        ),
    ]
    metadata_findings = metadata_blockers(local_index=local_index, sqlite_index=sqlite_index)
    supabase_metadata_findings = (
        supabase_metadata_blockers(supabase_index=supabase_index)
        if supabase_index is not None
        else []
    )
    blockers = [
        *record_parity_blockers(local_records=local_records, sqlite_records=sqlite_records),
        *record_boundary_findings,
        *metadata_findings,
        *supabase_metadata_findings,
        *search_blockers(search_results),
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
            "local_adapter_type": adapter_type(local_index),
            "sqlite_adapter_type": adapter_type(sqlite_index),
            "supabase_record_count": len(supabase_records) if supabase_index is not None else 0,
            "supabase_adapter_type": (
                adapter_type(supabase_index) if supabase_index is not None else "not_configured"
            ),
            "record_boundary_passed": not record_boundary_findings,
            "adapter_metadata_boundary_passed": not metadata_findings
            and not supabase_metadata_findings,
            "runtime_boundary_passed": not record_boundary_findings
            and not metadata_findings
            and not supabase_metadata_findings,
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
            "supabase": (
                supabase_index.describe_index() if supabase_index is not None else None
            ),
        },
        "search_cases": search_results,
        "future_backend_contracts": {
            "supabase": supabase_future_contract(supabase_index=supabase_index),
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

def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "AdapterHealthSearchCase",
    "DEFAULT_ADAPTER_HEALTH_SEARCH_CASES",
    "build_fooddb_index_adapter_health",
]
