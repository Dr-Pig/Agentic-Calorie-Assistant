from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_INPUTS = (
    "context_quality_pack",
    "short_term_context_runtime_replay",
    "context_conditioned_intent_wall",
    "context_coverage_matrix",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "short_term_context_runtime_replay": "accurate_intake_short_term_context_runtime_replay",
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "context_coverage_matrix": "accurate_intake_pl_ce_context_coverage_matrix",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_short_term_context_smoke": "accurate_intake_product_pages_short_term_context_smoke_v1",
    "product_pages_target_candidate_ui_smoke": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
}

EXPECTED_STATUSES = {
    "context_quality_pack": {"context_quality_diagnostic_pass"},
    "short_term_context_runtime_replay": {
        "runtime_replay_diagnostic_pass",
        "diagnostic_has_known_context_gaps",
    },
    "context_conditioned_intent_wall": {"pass"},
    "context_coverage_matrix": {
        "context_coverage_matrix_ready_for_human_review",
        "context_coverage_matrix_ready_with_known_runtime_gaps",
    },
    "product_pages_short_term_context_smoke": {"pass"},
    "product_pages_target_candidate_ui_smoke": {"pass"},
}

FORBIDDEN_TRUTHY_FLAGS = (
    "context_engineering_fault_claimed",
    "manager_context_packet_schema_changed",
    "deterministic_selected_target",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "runtime_truth_changed",
    "mutation_changed",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "context_quality_pack": (
        "short_term_context_runtime_replay_checked",
    ),
    "short_term_context_runtime_replay": (
        "runtime_trace_backed",
    ),
    "context_conditioned_intent_wall": (
        "manager_fixture_semantic_source_used",
    ),
    "product_pages_short_term_context_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "fixture_manager_used",
        "pending_followup_created",
        "pending_followup_reloaded",
        "context_policy_version_present",
        "loaded_context_summary_present",
        "omitted_context_summary_present",
        "pending_pins_present_after_followup",
        "chat_history_context_fields_reloaded",
        "assistant_followup_bubble_rendered",
        "assistant_commit_bubble_rendered",
        "product_pages_no_debug_trace",
    ),
    "product_pages_target_candidate_ui_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "chat_page_loaded",
        "chat_history_reloaded",
        "target_candidate_surface_checked",
        "target_candidate_list_read_only",
        "context_strip_read_only",
        "product_pages_no_debug_trace",
    ),
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {
            "",
            "0",
            "false",
            "no",
            "none",
            "null",
            "not_available",
            "not_checked",
        }
    return True


def _scenario_ids(payload: dict[str, Any]) -> set[str]:
    return {
        str(scenario.get("scenario_id") or "")
        for scenario in _list_value(payload.get("scenarios"))
        if isinstance(scenario, dict)
    }


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return _object_dict(payload.get("summary"))


def _flag(payload: dict[str, Any], summary: dict[str, Any], key: str) -> bool:
    return payload.get(key) is True or summary.get(key) is True


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") == "missing":
        return [f"{group_id}.missing"]
    if payload.get("artifact_type") == "invalid_json":
        return [f"{group_id}.invalid_json"]
    if payload.get("artifact_type") == "invalid_json_shape":
        return [f"{group_id}.invalid_json_shape"]
    expected_type = EXPECTED_ARTIFACT_TYPES.get(group_id)
    if expected_type and payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_smoke_id = EXPECTED_SMOKE_IDS.get(group_id)
    if expected_smoke_id and payload.get("smoke_id") != expected_smoke_id:
        blockers.append(f"{group_id}.unexpected_smoke_id:{payload.get('smoke_id')}")
    if _status(payload) not in EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _required_true_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for flag in REQUIRED_TRUE_FLAGS.get(group_id, ()):
        if payload.get(flag) is not True:
            suffix = "browser_not_executed" if flag == "browser_executed" else f"{flag}_not_true"
            blockers.append(f"{group_id}.{suffix}")
    return blockers


def _runtime_replay_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _int_value(payload.get("scenario_count")) < 7:
        blockers.append("short_term_context_runtime_replay.scenario_count_too_low")
    scenario_ids = _scenario_ids(payload)
    if "pending_followup_answer" not in scenario_ids:
        blockers.append("short_term_context_runtime_replay.pending_followup_answer_missing")
    if "long_chat_with_pinned_pending_draft" not in scenario_ids:
        blockers.append("short_term_context_runtime_replay.long_chat_with_pinned_pending_draft_missing")
    if "modify_drink_sugar" not in scenario_ids or "modify_rice_portion" not in scenario_ids:
        blockers.append("short_term_context_runtime_replay.correction_candidate_scenarios_missing")
    return blockers


def _intent_wall_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _summary(payload)
    if _int_value(summary.get("scenario_count")) < 11:
        blockers.append("context_conditioned_intent_wall.scenario_count_too_low")
    for flag in (
        "pending_followup_carryover",
        "ambiguity_preserved",
        "query_no_mutation",
        "target_update_requires_manager_decision",
    ):
        if not _flag(payload, summary, flag):
            blockers.append(f"context_conditioned_intent_wall.{flag}_not_true")
    return blockers


def _coverage_matrix_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _summary(payload)
    if _int_value(summary.get("covered_capability_count")) < 9:
        blockers.append("context_coverage_matrix.covered_capability_count_too_low")
    if _int_value(summary.get("blocked_capability_count")) > 0:
        blockers.append("context_coverage_matrix.blocked_capability_count_nonzero")
    matrix = _object_dict(payload.get("coverage_matrix"))
    for capability_id in (
        "pending_followup_carryover",
        "correction_target_candidates",
        "removal_target_candidates",
        "ambiguity_preserved",
        "long_session_bounded_context",
        "semantic_owner_boundary",
    ):
        entry = _object_dict(matrix.get(capability_id))
        if str(entry.get("coverage_status") or "not_checked") == "not_checked":
            blockers.append(f"context_coverage_matrix.{capability_id}_not_checked")
    return blockers


def _target_ui_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _int_value(payload.get("target_candidate_count_rendered")) != 2:
        blockers.append("product_pages_target_candidate_ui_smoke.target_candidate_count_rendered_mismatch")
    if list(payload.get("target_candidate_names_rendered") or []) != ["luwei", "milk tea"]:
        blockers.append("product_pages_target_candidate_ui_smoke.target_candidate_names_rendered_mismatch")
    if payload.get("manager_provider_call_count") != 0:
        blockers.append("product_pages_target_candidate_ui_smoke.manager_provider_call_count_not_zero")
    return blockers


def _input_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "smoke_id": payload.get("smoke_id") or "not_available",
            "status": payload.get("status") or "not_available",
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def build_session_context_carryover_qa_bundle_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {group_id: _object_dict(input_artifacts.get(group_id)) for group_id in REQUIRED_INPUTS}
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
        blockers.extend(_claim_blockers(group_id, payload))
        blockers.extend(_required_true_blockers(group_id, payload))
    blockers.extend(_runtime_replay_blockers(inputs["short_term_context_runtime_replay"]))
    blockers.extend(_intent_wall_blockers(inputs["context_conditioned_intent_wall"]))
    blockers.extend(_coverage_matrix_blockers(inputs["context_coverage_matrix"]))
    blockers.extend(_target_ui_blockers(inputs["product_pages_target_candidate_ui_smoke"]))
    blockers = list(dict.fromkeys(blockers))

    quality_summary = _summary(inputs["context_quality_pack"])
    coverage_summary = _summary(inputs["context_coverage_matrix"])
    runtime_ids = _scenario_ids(inputs["short_term_context_runtime_replay"])
    status = "session_context_carryover_qa_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_session_context_carryover_qa_bundle",
            "status": status,
            "claim_scope": "short_term_session_context_carryover_qa_for_human_review_only",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _input_statuses(inputs),
            "summary": {
                "pending_followup_carryover_checked": (
                    inputs["product_pages_short_term_context_smoke"].get("pending_followup_reloaded") is True
                    and "pending_followup_answer" in runtime_ids
                    and _flag(
                        inputs["context_conditioned_intent_wall"],
                        _summary(inputs["context_conditioned_intent_wall"]),
                        "pending_followup_carryover",
                    )
                ),
                "target_candidate_ui_checked": (
                    inputs["product_pages_target_candidate_ui_smoke"].get("target_candidate_surface_checked") is True
                ),
                "long_session_pinned_draft_checked": "long_chat_with_pinned_pending_draft" in runtime_ids,
                "context_conditioned_intent_wall_checked": (
                    inputs["context_conditioned_intent_wall"].get("manager_fixture_semantic_source_used") is True
                ),
                "quality_pending_pin_scenarios": _int_value(quality_summary.get("pending_pin_scenarios")),
                "quality_manager_semantic_required_scenarios": _int_value(
                    quality_summary.get("manager_semantic_required_scenarios")
                ),
                "coverage_known_runtime_gap_count": _int_value(
                    coverage_summary.get("known_runtime_gap_count")
                ),
                "coverage_blocked_capability_count": _int_value(
                    coverage_summary.get("blocked_capability_count")
                ),
            },
            "review_checkpoints": [
                "pending_followup_survives_reload_and_attaches_to_existing_draft",
                "target_candidates_render_as_read_only_context_not_frontend_selection",
                "long_session_keeps_pending_draft_hard_pinned",
                "context_conditioned_intent_wall_covers_query_mutation_target_update_boundaries",
                "semantic_owner_remains_fixture_manager_or_future_manager_not_deterministic_frontend",
            ],
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "frontend_semantic_owner": False,
            "frontend_selected_target": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
        }
    )


__all__ = [
    "REQUIRED_INPUTS",
    "build_session_context_carryover_qa_bundle_artifact",
]
