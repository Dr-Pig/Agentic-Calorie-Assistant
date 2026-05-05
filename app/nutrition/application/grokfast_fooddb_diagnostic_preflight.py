from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS as REQUIRED_FOODDB_GROKFAST_CASE_IDS,
)


EXPECTED_RETRIEVAL_EVAL_ARTIFACT = "accurate_intake_retrieval_eval_wall_v1"
EXPECTED_FOODDB_STATUS_ARTIFACT = "accurate_intake_fooddb_evidence_status_packet_v1"
EXPECTED_MANAGER_PACKET_ARTIFACT = "accurate_intake_fooddb_manager_packet_smoke"
EXPECTED_CASE_MATRIX_ARTIFACT = (
    "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix"
)
NEXT_GROKFAST_FOODDB_DIAGNOSTIC = "grokfast_fooddb_packet_live_diagnostic"


def build_grokfast_fooddb_diagnostic_preflight(
    *,
    retrieval_eval_wall_artifact: dict[str, Any],
    fooddb_status_packet: dict[str, Any],
    manager_packet_smoke_artifact: dict[str, Any],
    case_matrix_artifact: dict[str, Any],
) -> dict[str, Any]:
    retrieval_summary = _summary(retrieval_eval_wall_artifact)
    fooddb_summary = _summary(fooddb_status_packet)
    packet_summary = _summary(manager_packet_smoke_artifact)
    case_matrix_summary = _summary(case_matrix_artifact)
    blockers = [
        *_retrieval_eval_blockers(retrieval_eval_wall_artifact),
        *_fooddb_status_blockers(fooddb_status_packet),
        *_manager_packet_blockers(manager_packet_smoke_artifact),
        *_case_matrix_blockers(case_matrix_artifact),
    ]
    clear = not blockers

    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_live_diagnostic_preflight_only",
        "claim_scope": "grokfast_fooddb_packet_live_diagnostic_gate",
        "status": (
            "clear_for_grokfast_fooddb_packet_live_diagnostic" if clear else "blocked"
        ),
        "clear_to_run_live_diagnostic": clear,
        "next_required_slice": (
            NEXT_GROKFAST_FOODDB_DIAGNOSTIC
            if clear
            else "inspect_grokfast_fooddb_preflight_blockers"
        ),
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "preflight_inputs": {
            "retrieval_eval_wall_artifact_type": retrieval_eval_wall_artifact.get(
                "artifact_type"
            ),
            "fooddb_status_packet_artifact_type": fooddb_status_packet.get("artifact_type"),
            "manager_packet_smoke_artifact_type": manager_packet_smoke_artifact.get(
                "artifact_type"
            ),
            "case_matrix_artifact_type": case_matrix_artifact.get("artifact_type"),
        },
        "summary": {
            "retrieval_eval_fail_count": int(retrieval_summary.get("fail_count", 0) or 0),
            "retrieval_eval_next_required_slice": retrieval_summary.get(
                "next_required_slice"
            ),
            "websearch_runtime_truth_allowed_count": int(
                retrieval_summary.get("websearch_runtime_truth_allowed_count", 0) or 0
            ),
            "fooddb_next_required_slices": list(
                fooddb_status_packet.get("next_required_slices") or []
            ),
            "manager_fooddb_packet_seam_gate_status": fooddb_summary.get(
                "manager_fooddb_packet_seam_gate_status"
            ),
            "manager_contract_handoff_status": fooddb_summary.get(
                "manager_contract_handoff_status"
            ),
            "manager_contract_owner_handoff_ready": fooddb_summary.get(
                "manager_contract_owner_handoff_ready"
            )
            is True,
            "manager_packet_case_count": int(packet_summary.get("case_count", 0) or 0),
            "manager_packet_compact_pass_count": int(
                packet_summary.get("compact_packet_pass_count", 0) or 0
            ),
            "case_matrix_status": case_matrix_artifact.get("status"),
            "case_matrix_plan_only": case_matrix_artifact.get("plan_only") is True,
            "case_matrix_case_count": int(case_matrix_summary.get("case_count", 0) or 0),
            "case_matrix_modifier_guard_cases": int(
                case_matrix_summary.get("modifier_guard_cases", 0) or 0
            ),
            "case_matrix_bare_basket_cases": int(
                case_matrix_summary.get("bare_basket_cases", 0) or 0
            ),
            "case_matrix_listed_basket_cases": int(
                case_matrix_summary.get("listed_basket_cases", 0) or 0
            ),
            "case_matrix_websearch_cases": int(case_matrix_summary.get("websearch_cases", 0) or 0),
            "case_matrix_exact_card_cases": int(case_matrix_summary.get("exact_card_cases", 0) or 0),
            "case_matrix_live_provider_invoked": case_matrix_artifact.get(
                "live_provider_invoked"
            )
            is True,
            "case_matrix_websearch_invoked": case_matrix_artifact.get("websearch_invoked") is True,
            "case_matrix_shared_contract_changed": case_matrix_artifact.get(
                "shared_contract_changed"
            )
            is True,
            "case_matrix_non_claim_count": len(case_matrix_artifact.get("non_claims") or []),
        },
        "best_practice_basis": {
            "trace_level_eval": "run stage-specific preflight before provider diagnostic",
            "tool_loop_boundary": "live manager call can only consume read-only packet evidence",
            "structured_outputs_boundary": "preflight verifies upstream packet status, not semantic user intent",
        },
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_kimi_call",
            "no_readiness_claim",
            "no_self_use_approval",
        ],
    }


def is_grokfast_fooddb_preflight_clear(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type") == "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1"
        and not _preflight_artifact_integrity_blockers(artifact)
    )


def _retrieval_eval_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != EXPECTED_RETRIEVAL_EVAL_ARTIFACT:
        blockers.append("unsupported_retrieval_eval_wall_artifact")
        return blockers
    summary = _summary(artifact)
    if int(summary.get("fail_count", 0) or 0) != 0:
        blockers.append("retrieval_eval_wall_has_failures")
    if summary.get("next_required_slice") != NEXT_GROKFAST_FOODDB_DIAGNOSTIC:
        blockers.append("retrieval_eval_wall_not_pointing_to_grokfast_diagnostic")
    if int(summary.get("websearch_runtime_truth_allowed_count", 0) or 0) != 0:
        blockers.append("websearch_runtime_truth_leaked_before_live_diagnostic")
    if artifact.get("live_provider_used") is not False:
        blockers.append("retrieval_eval_wall_used_live_provider")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("retrieval_eval_wall_used_live_websearch")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("retrieval_eval_wall_claimed_readiness")
    return blockers


def _fooddb_status_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != EXPECTED_FOODDB_STATUS_ARTIFACT:
        blockers.append("unsupported_fooddb_status_packet_artifact")
        return blockers
    next_slices = list(artifact.get("next_required_slices") or [])
    if next_slices != [NEXT_GROKFAST_FOODDB_DIAGNOSTIC]:
        blockers.append("fooddb_status_not_ready_for_grokfast_diagnostic")
    if artifact.get("live_provider_used") is not False:
        blockers.append("fooddb_status_used_live_provider")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("fooddb_status_used_live_websearch")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("fooddb_status_claimed_readiness")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_status_changed_runtime_truth")
    summary = _summary(artifact)
    if summary.get("manager_fooddb_packet_seam_gate_status") != "pass":
        blockers.append("manager_fooddb_packet_seam_gate_not_pass")
    if summary.get("manager_contract_owner_handoff_ready") is True:
        blockers.append("manager_contract_owner_handoff_ready")
    handoff_status = str(summary.get("manager_contract_handoff_status") or "not_run")
    if handoff_status not in {"not_run", "fooddb_contract_unblocked"}:
        blockers.append("manager_contract_handoff_blocks_fooddb_live_diagnostic")
    return blockers


def _manager_packet_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != EXPECTED_MANAGER_PACKET_ARTIFACT:
        blockers.append("unsupported_manager_packet_smoke_artifact")
        return blockers
    summary = _summary(artifact)
    case_count = int(summary.get("case_count", 0) or 0)
    compact_pass_count = int(summary.get("compact_packet_pass_count", 0) or 0)
    if case_count <= 0:
        blockers.append("manager_packet_smoke_has_no_cases")
    if compact_pass_count != case_count:
        blockers.append("manager_packet_smoke_not_all_compact")
    if (
        summary.get("raw_source_rows_included") is not False
        or summary.get("candidate_only_records_included") is not False
        or summary.get("full_fooddb_included") is not False
    ):
        blockers.append("manager_packet_smoke_not_compact")
    if artifact.get("live_provider_used") is not False:
        blockers.append("manager_packet_smoke_used_live_provider")
    if artifact.get("readiness_claimed") is True:
        blockers.append("manager_packet_smoke_claimed_readiness")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("manager_packet_smoke_changed_runtime_truth")
    if artifact.get("mutation_changed") is True or artifact.get("runtime_mutation_attempted") is True:
        blockers.append("manager_packet_smoke_attempted_mutation")
    if artifact.get("manager_context_changed") is not False:
        blockers.append("manager_packet_smoke_changed_manager_context")
    if artifact.get("packetizer_format_changed") is not False:
        blockers.append("manager_packet_smoke_changed_packetizer_format")
    return blockers


def _case_matrix_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != EXPECTED_CASE_MATRIX_ARTIFACT:
        blockers.append("unsupported_fooddb_grokfast_case_matrix_artifact")
        return blockers
    summary = _summary(artifact)
    if artifact.get("status") != "pass":
        blockers.append("fooddb_grokfast_case_matrix_not_pass")
    if artifact.get("plan_only") is not True:
        blockers.append("fooddb_grokfast_case_matrix_not_plan_only")
    if artifact.get("live_llm_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_live_llm")
    if artifact.get("live_provider_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_live_provider")
    if artifact.get("websearch_invoked") is not False:
        blockers.append("fooddb_grokfast_case_matrix_invoked_websearch")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_mutation")
    if artifact.get("manager_context_packet_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_manager_context")
    if artifact.get("shared_contract_changed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_changed_shared_contract")
    if artifact.get("product_readiness_claimed") is not False:
        blockers.append("fooddb_grokfast_case_matrix_claimed_readiness")
    if artifact.get("private_self_use_approved") is not False:
        blockers.append("fooddb_grokfast_case_matrix_claimed_self_use_approval")
    if int(summary.get("case_count", 0) or 0) < 5:
        blockers.append("fooddb_grokfast_case_matrix_too_few_cases")
    case_ids = [
        str(case.get("case_id") or "")
        for case in artifact.get("cases") or []
        if isinstance(case, dict)
    ]
    if case_ids != list(REQUIRED_FOODDB_GROKFAST_CASE_IDS):
        blockers.append("fooddb_grokfast_case_matrix_required_case_order_mismatch")
    if int(summary.get("modifier_guard_cases", 0) or 0) < 2:
        blockers.append("fooddb_grokfast_case_matrix_missing_modifier_guard_cases")
    if int(summary.get("bare_basket_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_bare_basket_case")
    if int(summary.get("listed_basket_cases", 0) or 0) < 1:
        blockers.append("fooddb_grokfast_case_matrix_missing_listed_basket_case")
    if int(summary.get("websearch_cases", 0) or 0) != 0:
        blockers.append("fooddb_grokfast_case_matrix_includes_websearch_cases")
    if int(summary.get("exact_card_cases", 0) or 0) != 0:
        blockers.append("fooddb_grokfast_case_matrix_includes_exact_card_cases")
    non_claims = set(artifact.get("non_claims") or [])
    for required in (
        "not_full_self_use_gate",
        "not_websearch_exact_card_gate",
        "not_final_response_quality_gate",
        "not_production_readiness",
        "not_private_self_use_approval",
        "not_kimi_activation",
        "not_runtime_mutation_gate",
    ):
        if required not in non_claims:
            blockers.append(f"fooddb_grokfast_case_matrix_missing_non_claim.{required}")
    return blockers


def _preflight_artifact_integrity_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("status") != "clear_for_grokfast_fooddb_packet_live_diagnostic":
        blockers.append("preflight_status_not_clear")
    if artifact.get("clear_to_run_live_diagnostic") is not True:
        blockers.append("preflight_clear_flag_not_true")
    if artifact.get("blockers"):
        blockers.append("preflight_has_blockers")
    if artifact.get("next_required_slice") != NEXT_GROKFAST_FOODDB_DIAGNOSTIC:
        blockers.append("preflight_next_slice_not_grokfast_fooddb_diagnostic")
    for key, blocker in (
        ("runtime_truth_changed", "preflight_changed_runtime_truth"),
        ("mutation_changed", "preflight_changed_mutation"),
        ("manager_context_changed", "preflight_changed_manager_context"),
        ("packetizer_format_changed", "preflight_changed_packetizer_format"),
        ("live_provider_used", "preflight_already_used_live_provider"),
        ("live_websearch_used", "preflight_already_used_live_websearch"),
        ("readiness_claimed", "preflight_claimed_readiness"),
        ("self_use_approved", "preflight_claimed_self_use_approval"),
        ("production_selected", "preflight_claimed_production_model"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)

    summary = _summary(artifact)
    if int(summary.get("retrieval_eval_fail_count", 0) or 0) != 0:
        blockers.append("preflight_summary_retrieval_failures")
    if summary.get("retrieval_eval_next_required_slice") != NEXT_GROKFAST_FOODDB_DIAGNOSTIC:
        blockers.append("preflight_summary_retrieval_next_slice_mismatch")
    if int(summary.get("websearch_runtime_truth_allowed_count", 0) or 0) != 0:
        blockers.append("preflight_summary_websearch_runtime_truth_leak")
    if list(summary.get("fooddb_next_required_slices") or []) != [NEXT_GROKFAST_FOODDB_DIAGNOSTIC]:
        blockers.append("preflight_summary_fooddb_next_slices_mismatch")
    if summary.get("manager_fooddb_packet_seam_gate_status") != "pass":
        blockers.append("preflight_summary_manager_packet_seam_not_pass")
    if summary.get("manager_contract_owner_handoff_ready") is not False:
        blockers.append("preflight_summary_manager_handoff_ready")
    if str(summary.get("manager_contract_handoff_status") or "not_run") not in {
        "not_run",
        "fooddb_contract_unblocked",
    }:
        blockers.append("preflight_summary_manager_handoff_blocks")
    case_count = int(summary.get("manager_packet_case_count", 0) or 0)
    compact_pass_count = int(summary.get("manager_packet_compact_pass_count", 0) or 0)
    if case_count <= 0:
        blockers.append("preflight_summary_packet_cases_missing")
    if compact_pass_count != case_count:
        blockers.append("preflight_summary_packet_compact_count_mismatch")
    if summary.get("case_matrix_status") != "pass":
        blockers.append("preflight_summary_case_matrix_not_pass")
    if summary.get("case_matrix_plan_only") is not True:
        blockers.append("preflight_summary_case_matrix_not_plan_only")
    if int(summary.get("case_matrix_case_count", 0) or 0) < 5:
        blockers.append("preflight_summary_case_matrix_too_few_cases")
    if int(summary.get("case_matrix_modifier_guard_cases", 0) or 0) < 2:
        blockers.append("preflight_summary_case_matrix_missing_modifier_cases")
    if int(summary.get("case_matrix_bare_basket_cases", 0) or 0) < 1:
        blockers.append("preflight_summary_case_matrix_missing_bare_basket")
    if int(summary.get("case_matrix_listed_basket_cases", 0) or 0) < 1:
        blockers.append("preflight_summary_case_matrix_missing_listed_basket")
    if int(summary.get("case_matrix_websearch_cases", 0) or 0) != 0:
        blockers.append("preflight_summary_case_matrix_websearch_cases")
    if int(summary.get("case_matrix_exact_card_cases", 0) or 0) != 0:
        blockers.append("preflight_summary_case_matrix_exact_card_cases")
    if summary.get("case_matrix_live_provider_invoked") is not False:
        blockers.append("preflight_summary_case_matrix_live_provider_invoked")
    if summary.get("case_matrix_websearch_invoked") is not False:
        blockers.append("preflight_summary_case_matrix_websearch_invoked")
    if summary.get("case_matrix_shared_contract_changed") is not False:
        blockers.append("preflight_summary_case_matrix_shared_contract_changed")
    if int(summary.get("case_matrix_non_claim_count", 0) or 0) < 7:
        blockers.append("preflight_summary_case_matrix_missing_non_claims")
    return blockers


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary")
    return dict(summary) if isinstance(summary, dict) else {}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "NEXT_GROKFAST_FOODDB_DIAGNOSTIC",
    "build_grokfast_fooddb_diagnostic_preflight",
    "is_grokfast_fooddb_preflight_clear",
]
