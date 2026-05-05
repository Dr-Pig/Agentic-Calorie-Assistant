from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_retrieval_policy import IndexedFoodRecord
from .retrieval_eval_wall_case_utils import websearch_runtime_truth_allowed_count
from .retrieval_eval_wall_evidence_cases import (
    build_grounding_cases,
    build_negative_cases,
    build_ranking_cases,
)
from .retrieval_eval_wall_route_cases import build_source_selection_cases
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic


def build_retrieval_eval_wall(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    websearch_pipeline_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    websearch_pipeline = websearch_pipeline_artifact or build_websearch_candidate_pipeline_diagnostic()
    source_selection_cases = build_source_selection_cases()
    ranking_cases = build_ranking_cases(retrieval_records)
    grounding_cases = build_grounding_cases(retrieval_records, websearch_pipeline=websearch_pipeline)
    negative_cases = build_negative_cases(retrieval_records, websearch_pipeline=websearch_pipeline)
    all_cases = [*source_selection_cases, *ranking_cases, *grounding_cases, *negative_cases]
    fail_count = sum(1 for case in all_cases if case["status"] != "pass")
    return {
        "artifact_type": "accurate_intake_retrieval_eval_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retrieval_eval_wall_only",
        "claim_scope": "retrieval_source_ranking_grounding_negative_eval",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "best_practice_basis": {
            "trace_level_eval": "separate source selection, ranking, grounding, and negative cases",
            "retrieval_first": "typed retrieval packet before manager synthesis",
            "tool_loop_boundary": "retrieval tools provide data only; manager/runtime guard own later synthesis and mutation",
        },
        "source_selection_cases": source_selection_cases,
        "ranking_cases": ranking_cases,
        "grounding_cases": grounding_cases,
        "negative_cases": negative_cases,
        "summary": {
            "case_count": len(all_cases),
            "source_selection_case_count": len(source_selection_cases),
            "ranking_case_count": len(ranking_cases),
            "grounding_case_count": len(grounding_cases),
            "negative_case_count": len(negative_cases),
            "pass_count": sum(1 for case in all_cases if case["status"] == "pass"),
            "fail_count": fail_count,
            "websearch_runtime_truth_allowed_count": websearch_runtime_truth_allowed_count(
                websearch_pipeline
            ),
            "next_required_slice": (
                "inspect_retrieval_eval_wall_failures"
                if fail_count
                else "grokfast_fooddb_packet_live_diagnostic"
            ),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_retrieval_eval_wall"]
