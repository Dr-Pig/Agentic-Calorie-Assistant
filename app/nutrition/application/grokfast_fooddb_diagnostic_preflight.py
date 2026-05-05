from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


EXPECTED_RETRIEVAL_EVAL_ARTIFACT = "accurate_intake_retrieval_eval_wall_v1"
EXPECTED_FOODDB_STATUS_ARTIFACT = "accurate_intake_fooddb_evidence_status_packet_v1"
EXPECTED_MANAGER_PACKET_ARTIFACT = "accurate_intake_fooddb_manager_packet_smoke"
EXPECTED_FOODDB_ACTIVATION_WALL_ARTIFACT = "accurate_intake_fooddb_activation_wall_v1"
EXPECTED_LOCAL_ACTIVATION_SCENARIO_WALL_ARTIFACT = (
    "accurate_intake_fooddb_local_activation_scenario_wall_v1"
)
NEXT_GROKFAST_FOODDB_DIAGNOSTIC = "grokfast_fooddb_packet_live_diagnostic"


def build_grokfast_fooddb_diagnostic_preflight(
    *,
    retrieval_eval_wall_artifact: dict[str, Any],
    fooddb_status_packet: dict[str, Any],
    manager_packet_smoke_artifact: dict[str, Any],
    fooddb_activation_wall_artifact: dict[str, Any] | None = None,
    local_activation_scenario_wall_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retrieval_summary = _summary(retrieval_eval_wall_artifact)
    fooddb_summary = _summary(fooddb_status_packet)
    packet_summary = _summary(manager_packet_smoke_artifact)
    activation_summary = _summary(fooddb_activation_wall_artifact or {})
    scenario_summary = _summary(local_activation_scenario_wall_artifact or {})
    blockers = [
        *_retrieval_eval_blockers(retrieval_eval_wall_artifact),
        *_fooddb_status_blockers(fooddb_status_packet),
        *_manager_packet_blockers(manager_packet_smoke_artifact),
        *_fooddb_activation_wall_blockers(fooddb_activation_wall_artifact),
        *_local_activation_scenario_wall_blockers(local_activation_scenario_wall_artifact),
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
            "fooddb_activation_wall_artifact_type": (
                fooddb_activation_wall_artifact or {}
            ).get("artifact_type"),
            "local_activation_scenario_wall_artifact_type": (
                local_activation_scenario_wall_artifact or {}
            ).get("artifact_type"),
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
            "fooddb_activation_wall_status": (fooddb_activation_wall_artifact or {}).get("status"),
            "fooddb_activation_wall_upstream_next_required_slices": list(
                (fooddb_activation_wall_artifact or {}).get("upstream_next_required_slices")
                or []
            ),
            "local_activation_scenario_wall_status": (
                local_activation_scenario_wall_artifact or {}
            ).get("status"),
            "local_activation_scenario_wall_upstream_next_required_slices": list(
                (local_activation_scenario_wall_artifact or {}).get(
                    "upstream_next_required_slices"
                )
                or []
            ),
            "local_activation_scenario_wall_fooddb_packet_pass_turn_count": int(
                scenario_summary.get("fooddb_packet_pass_turn_count", 0) or 0
            ),
            "local_activation_scenario_wall_fooddb_packet_required_turn_count": int(
                scenario_summary.get("fooddb_packet_required_turn_count", 0) or 0
            ),
            "fooddb_activation_wall_p0_supported_modifier_count": int(
                activation_summary.get("p0_supported_modifier_count", 0) or 0
            ),
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


def _fooddb_activation_wall_blockers(artifact: dict[str, Any] | None) -> list[str]:
    blockers: list[str] = []
    if not isinstance(artifact, dict):
        return ["missing_fooddb_activation_wall_artifact"]
    if artifact.get("artifact_type") != EXPECTED_FOODDB_ACTIVATION_WALL_ARTIFACT:
        blockers.append("unsupported_fooddb_activation_wall_artifact")
        return blockers
    if artifact.get("status") != "pass":
        blockers.append("fooddb_activation_wall_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_activation_wall_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("fooddb_activation_wall_changed_mutation")
    if artifact.get("manager_context_changed") is not False:
        blockers.append("fooddb_activation_wall_changed_manager_context")
    if artifact.get("packetizer_format_changed") is not False:
        blockers.append("fooddb_activation_wall_changed_packetizer_format")
    if artifact.get("live_provider_used") is not False:
        blockers.append("fooddb_activation_wall_used_live_provider")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("fooddb_activation_wall_used_live_websearch")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("fooddb_activation_wall_claimed_readiness")
    next_required = list(artifact.get("upstream_next_required_slices") or [])
    if next_required != [NEXT_GROKFAST_FOODDB_DIAGNOSTIC]:
        blockers.append("fooddb_activation_wall_next_step_not_grokfast_fooddb_diagnostic")
    summary = _summary(artifact)
    if int(summary.get("p0_supported_modifier_count", 0) or 0) < 3:
        blockers.append("fooddb_activation_wall_p0_modifier_coverage_missing")
    return blockers


def _local_activation_scenario_wall_blockers(artifact: dict[str, Any] | None) -> list[str]:
    blockers: list[str] = []
    if not isinstance(artifact, dict):
        return ["missing_local_activation_scenario_wall_artifact"]
    if artifact.get("artifact_type") != EXPECTED_LOCAL_ACTIVATION_SCENARIO_WALL_ARTIFACT:
        blockers.append("unsupported_local_activation_scenario_wall_artifact")
        return blockers
    if artifact.get("status") != "pass":
        blockers.append("local_activation_scenario_wall_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("local_activation_scenario_wall_changed_runtime_truth")
    if artifact.get("mutation_changed") is not False:
        blockers.append("local_activation_scenario_wall_changed_mutation")
    if artifact.get("manager_context_changed") is not False:
        blockers.append("local_activation_scenario_wall_changed_manager_context")
    if artifact.get("packetizer_format_changed") is not False:
        blockers.append("local_activation_scenario_wall_changed_packetizer_format")
    if artifact.get("live_provider_used") is not False:
        blockers.append("local_activation_scenario_wall_used_live_provider")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("local_activation_scenario_wall_used_live_websearch")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("local_activation_scenario_wall_claimed_readiness")
    if artifact.get("runner_inferred_semantics") is not False:
        blockers.append("local_activation_scenario_wall_inferred_semantics")
    next_required = list(artifact.get("upstream_next_required_slices") or [])
    if next_required != [NEXT_GROKFAST_FOODDB_DIAGNOSTIC]:
        blockers.append("local_activation_scenario_wall_next_step_not_grokfast_fooddb_diagnostic")
    summary = _summary(artifact)
    required_turns = int(summary.get("fooddb_packet_required_turn_count", 0) or 0)
    pass_turns = int(summary.get("fooddb_packet_pass_turn_count", 0) or 0)
    if required_turns <= 0:
        blockers.append("local_activation_scenario_wall_missing_fooddb_packet_turns")
    if pass_turns != required_turns:
        blockers.append("local_activation_scenario_wall_packet_turn_failures")
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
    if summary.get("fooddb_activation_wall_status") != "pass":
        blockers.append("preflight_summary_activation_wall_not_pass")
    if list(summary.get("fooddb_activation_wall_upstream_next_required_slices") or []) != [
        NEXT_GROKFAST_FOODDB_DIAGNOSTIC
    ]:
        blockers.append("preflight_summary_activation_wall_next_slice_mismatch")
    if summary.get("local_activation_scenario_wall_status") != "pass":
        blockers.append("preflight_summary_local_scenario_wall_not_pass")
    if list(summary.get("local_activation_scenario_wall_upstream_next_required_slices") or []) != [
        NEXT_GROKFAST_FOODDB_DIAGNOSTIC
    ]:
        blockers.append("preflight_summary_local_scenario_wall_next_slice_mismatch")
    scenario_required_turns = int(
        summary.get("local_activation_scenario_wall_fooddb_packet_required_turn_count", 0) or 0
    )
    scenario_pass_turns = int(
        summary.get("local_activation_scenario_wall_fooddb_packet_pass_turn_count", 0) or 0
    )
    if scenario_required_turns <= 0:
        blockers.append("preflight_summary_local_scenario_missing_fooddb_packet_turns")
    if scenario_pass_turns != scenario_required_turns:
        blockers.append("preflight_summary_local_scenario_packet_turn_mismatch")
    if int(summary.get("fooddb_activation_wall_p0_supported_modifier_count", 0) or 0) < 3:
        blockers.append("preflight_summary_activation_wall_p0_modifier_coverage_missing")
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
