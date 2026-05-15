from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.current_shell_context_coverage_matrix_entries import (
    build_context_coverage_matrix,
)
from app.composition.current_shell_context_coverage_matrix_policy import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_STATUSES,
    REQUIRED_INPUTS,
    _input_blockers,
    _input_statuses,
    _int_value,
    _summary,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_pl_ce_context_coverage_matrix_artifact(
    *,
    context_conditioned_intent_wall: dict[str, Any],
    short_term_context_runtime_replay: dict[str, Any],
    fake_provider_context_smoke: dict[str, Any],
    context_quality_pack: dict[str, Any],
) -> dict[str, Any]:
    inputs = {
        "context_conditioned_intent_wall": _object_dict(context_conditioned_intent_wall),
        "short_term_context_runtime_replay": _object_dict(short_term_context_runtime_replay),
        "fake_provider_context_smoke": _object_dict(fake_provider_context_smoke),
        "context_quality_pack": _object_dict(context_quality_pack),
    }
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_input_blockers(group_id, payload))
    matrix = build_context_coverage_matrix(inputs)
    for entry in matrix.values():
        blockers.extend(entry["blockers"])
    blockers = list(dict.fromkeys(blockers))

    runtime_summary = _summary(inputs["short_term_context_runtime_replay"])
    known_gap_signals = list(runtime_summary.get("known_gap_signals") or [])
    known_runtime_gap_count = _int_value(runtime_summary.get("current_gap_scenarios"))
    if (
        inputs["short_term_context_runtime_replay"].get("status")
        == "diagnostic_has_known_context_gaps"
        or known_gap_signals
    ) and known_runtime_gap_count == 0:
        known_runtime_gap_count = max(1, len(known_gap_signals))
    if blockers:
        status = "blocked"
    elif known_runtime_gap_count:
        status = "context_coverage_matrix_ready_with_known_runtime_gaps"
    else:
        status = "context_coverage_matrix_ready_for_human_review"
    covered_capability_count = sum(
        1 for entry in matrix.values() if entry["coverage_status"] != "not_checked"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "claim_scope": "pl_ce_short_term_context_coverage_matrix_for_human_review",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": status,
            "blockers": blockers,
            "input_statuses": _input_statuses(inputs),
            "coverage_matrix": matrix,
            "summary": {
                "capability_count": len(matrix),
                "covered_capability_count": covered_capability_count,
                "known_runtime_gap_count": known_runtime_gap_count,
                "blocked_capability_count": sum(1 for entry in matrix.values() if entry["blockers"]),
            },
            "known_runtime_gap_signals": known_gap_signals,
            "autofix_attempted": False,
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "human_review_required": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "REQUIRED_INPUTS",
    "build_pl_ce_context_coverage_matrix_artifact",
]
