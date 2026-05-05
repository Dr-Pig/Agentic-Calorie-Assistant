from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_INPUTS = (
    "context_conditioned_intent_wall",
    "contextual_interaction_matrix",
    "fake_provider_context_smoke",
    "responder_input_contract_fake_smoke",
    "context_coverage_matrix",
    "session_context_carryover_qa_bundle",
    "ui_context_alignment_pack",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "contextual_interaction_matrix": "accurate_intake_contextual_interaction_matrix",
    "fake_provider_context_smoke": "accurate_intake_fake_provider_context_smoke",
    "responder_input_contract_fake_smoke": "accurate_intake_responder_input_contract_fake_smoke",
    "context_coverage_matrix": "accurate_intake_pl_ce_context_coverage_matrix",
    "session_context_carryover_qa_bundle": "accurate_intake_session_context_carryover_qa_bundle",
    "ui_context_alignment_pack": "accurate_intake_pl_ce_ui_context_alignment_pack",
}

EXPECTED_STATUSES = {
    "context_conditioned_intent_wall": {"pass"},
    "contextual_interaction_matrix": {"pass"},
    "fake_provider_context_smoke": {"pass"},
    "responder_input_contract_fake_smoke": {"pass"},
    "context_coverage_matrix": {
        "context_coverage_matrix_ready_for_human_review",
        "context_coverage_matrix_ready_with_known_runtime_gaps",
    },
    "session_context_carryover_qa_bundle": {"session_context_carryover_qa_ready_for_human_review"},
    "ui_context_alignment_pack": {"ui_context_alignment_ready_for_human_review"},
}

FORBIDDEN_TRUTHY_FLAGS = (
    "context_engineering_fault_claimed",
    "manager_context_packet_schema_changed",
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "frontend_semantic_owner",
    "frontend_selects_target",
    "mutation_authority",
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "live_provider_invoked",
    "web_tavily_used",
    "web_tavily_invoked",
    "live_websearch_used",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_used",
    "fooddb_truth_changed",
    "fooddb_truth_updated",
    "runtime_truth_changed",
    "mutation_changed",
    "writes_performed",
    "import_allowed",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "canonical_eval_promoted",
)


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


def _nested_forbidden_blockers(group_id: str, value: Any, path: str = "") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_TRUTHY_FLAGS and _claim_is_true(nested_value):
                blockers.append(f"{group_id}.{nested_path}")
            blockers.extend(_nested_forbidden_blockers(group_id, nested_value, nested_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            blockers.extend(_nested_forbidden_blockers(group_id, item, f"{path}[{index}]"))
    return list(dict.fromkeys(blockers))


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return _object_dict(payload.get("summary"))


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_type") == "missing":
        return [f"{group_id}.missing"]
    if payload.get("artifact_type") == "invalid_json":
        return [f"{group_id}.invalid_json"]
    if payload.get("artifact_type") == "invalid_json_shape":
        return [f"{group_id}.invalid_json_shape"]
    expected_type = EXPECTED_ARTIFACT_TYPES[group_id]
    if payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    if _status(payload) not in EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
        blockers.extend(
            f"{group_id}.{blocker}"
            for blocker in _list_value(payload.get("blockers"))
            if str(blocker or "").strip()
        )
    for flag in FORBIDDEN_TRUTHY_FLAGS:
        if _claim_is_true(payload.get(flag)):
            blockers.append(f"{group_id}.{flag}")
    blockers.extend(_nested_forbidden_blockers(group_id, payload))
    return list(dict.fromkeys(blockers))


def _intent_wall_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if payload.get("manager_fixture_semantic_source_used") is not True:
        blockers.append("context_conditioned_intent_wall.manager_fixture_semantic_source_missing")
    if _int_value(summary.get("scenario_count")) < 11:
        blockers.append("context_conditioned_intent_wall.scenario_count_too_low")
    for flag in (
        "pending_followup_carryover",
        "ambiguity_preserved",
        "query_no_mutation",
        "target_update_requires_manager_decision",
    ):
        if payload.get(flag) is not True and summary.get(flag) is not True:
            blockers.append(f"context_conditioned_intent_wall.{flag}_not_true")
    return blockers


def _interaction_matrix_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if payload.get("semantic_owner") != "fixture_manager_structured_decision":
        blockers.append("contextual_interaction_matrix.semantic_owner_not_fixture_manager")
    if payload.get("manager_fixture_semantic_source_used") is not True:
        blockers.append("contextual_interaction_matrix.manager_fixture_semantic_source_missing")
    if payload.get("frontend_render_only") is not True:
        blockers.append("contextual_interaction_matrix.frontend_render_only_not_true")
    expected_minimums = {
        "interaction_count": 11,
        "pending_followup_interactions": 1,
        "target_candidate_interactions": 4,
        "ambiguity_preserved_interactions": 2,
        "query_no_mutation_interactions": 1,
        "target_update_manager_decision_interactions": 1,
    }
    for key, minimum in expected_minimums.items():
        if _int_value(summary.get(key)) < minimum:
            blockers.append(f"contextual_interaction_matrix.{key}_too_low")
    return blockers


def _fake_provider_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if payload.get("final_semantic_decision_source") != "fixture_manager_structured_decision":
        blockers.append("fake_provider_context_smoke.semantic_source_not_fixture_manager")
    if payload.get("manager_handoff_matrix_checked") is not True:
        blockers.append("fake_provider_context_smoke.manager_handoff_matrix_missing")
    if _int_value(summary.get("manager_handoff_scenario_count")) < 6:
        blockers.append("fake_provider_context_smoke.manager_handoff_scenario_count_too_low")
    if _int_value(summary.get("ambiguous_back_reference_scenarios")) < 1:
        blockers.append("fake_provider_context_smoke.ambiguous_back_reference_missing")
    return blockers


def _responder_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if _int_value(summary.get("scenario_count")) < 5:
        blockers.append("responder_input_contract_fake_smoke.scenario_count_too_low")
    for scenario in _list_value(payload.get("scenarios")):
        if not isinstance(scenario, dict):
            continue
        scenario_id = str(scenario.get("scenario_id") or "unknown")
        if scenario.get("fake_responder_used") is not True:
            blockers.append(f"responder_input_contract_fake_smoke.{scenario_id}.fake_responder_missing")
        if scenario.get("responder_claims_require_allowed_fact_id") is not True:
            blockers.append(
                f"responder_input_contract_fake_smoke.{scenario_id}.allowed_fact_requirement_missing"
            )
        if scenario.get("raw_text_claim_grading_used") is not False:
            blockers.append(
                f"responder_input_contract_fake_smoke.{scenario_id}.raw_text_claim_grading_used"
            )
    return blockers


def _coverage_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if _int_value(summary.get("covered_capability_count")) < 9:
        blockers.append("context_coverage_matrix.covered_capability_count_too_low")
    if _int_value(summary.get("blocked_capability_count")) > 0:
        blockers.append("context_coverage_matrix.blocked_capability_count_present")
    if _int_value(summary.get("known_runtime_gap_count")) > 0:
        blockers.append("context_coverage_matrix.known_runtime_gap_count_present")
    return blockers


def _session_carryover_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    for key in (
        "pending_followup_carryover_checked",
        "target_candidate_ui_checked",
        "long_session_pinned_draft_checked",
        "context_conditioned_intent_wall_checked",
    ):
        if summary.get(key) is not True:
            blockers.append(f"session_context_carryover_qa_bundle.{key}_not_true")
    if _int_value(summary.get("coverage_known_runtime_gap_count")) > 0:
        blockers.append("session_context_carryover_qa_bundle.coverage_known_runtime_gap_present")
    return blockers


def _ui_alignment_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    blockers: list[str] = []
    if payload.get("render_only_boundary_ok") is not True:
        blockers.append("ui_context_alignment_pack.render_only_boundary_not_ok")
    if payload.get("frontend_semantic_owner") is not False:
        blockers.append("ui_context_alignment_pack.frontend_semantic_owner")
    if summary.get("chat_context_reload_checked") is not True:
        blockers.append("ui_context_alignment_pack.chat_context_reload_not_checked")
    if summary.get("seven_day_diary_checked") is not True:
        blockers.append("ui_context_alignment_pack.seven_day_diary_not_checked")
    if summary.get("body_read_model_checked") is not True:
        blockers.append("ui_context_alignment_pack.body_read_model_not_checked")
    return blockers


def _artifact_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": payload.get("status") or "not_available",
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def build_manager_intent_readiness_review_pack_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = {group_id: _object_dict(input_artifacts.get(group_id)) for group_id in REQUIRED_INPUTS}
    blockers: list[str] = []
    for group_id, payload in inputs.items():
        blockers.extend(_identity_blockers(group_id, payload))
    blockers.extend(_intent_wall_blockers(inputs["context_conditioned_intent_wall"]))
    blockers.extend(_interaction_matrix_blockers(inputs["contextual_interaction_matrix"]))
    blockers.extend(_fake_provider_blockers(inputs["fake_provider_context_smoke"]))
    blockers.extend(_responder_blockers(inputs["responder_input_contract_fake_smoke"]))
    blockers.extend(_coverage_blockers(inputs["context_coverage_matrix"]))
    blockers.extend(_session_carryover_blockers(inputs["session_context_carryover_qa_bundle"]))
    blockers.extend(_ui_alignment_blockers(inputs["ui_context_alignment_pack"]))
    blockers = list(dict.fromkeys(blockers))

    context_wall_summary = _summary(inputs["context_conditioned_intent_wall"])
    interaction_summary = _summary(inputs["contextual_interaction_matrix"])
    fake_provider_summary = _summary(inputs["fake_provider_context_smoke"])
    responder_summary = _summary(inputs["responder_input_contract_fake_smoke"])
    coverage_summary = _summary(inputs["context_coverage_matrix"])
    session_summary = _summary(inputs["session_context_carryover_qa_bundle"])
    ui_summary = _summary(inputs["ui_context_alignment_pack"])
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_manager_intent_readiness_review_pack",
            "status": "manager_intent_readiness_ready_for_human_review"
            if not blockers
            else "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_short_term_manager_intent_readiness_review_only",
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "included_artifact_statuses": _artifact_statuses(inputs),
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "human_review_required": True,
            "review_required_before_provider_call": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
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
            "manager_context_packet_schema_changed": False,
            "context_engineering_fault_claimed": False,
            "mutation_authority": False,
            "deterministic_semantic_inference_used": False,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "frontend_semantic_owner": False,
            "semantic_owner": "fixture_manager_structured_decision",
            "deterministic_role": "supply_context_candidates_pins_omission_trace_and_validate_boundaries",
            "manager_role": "semantic_decision_owner_in_fixture_or_future_live_diagnostic",
            "summary": {
                "intent_wall_scenarios": _int_value(context_wall_summary.get("scenario_count")),
                "contextual_interactions": _int_value(interaction_summary.get("interaction_count")),
                "pending_followup_interactions": _int_value(
                    interaction_summary.get("pending_followup_interactions")
                ),
                "target_candidate_interactions": _int_value(
                    interaction_summary.get("target_candidate_interactions")
                ),
                "ambiguity_preserved_interactions": _int_value(
                    interaction_summary.get("ambiguity_preserved_interactions")
                ),
                "query_no_mutation_interactions": _int_value(
                    interaction_summary.get("query_no_mutation_interactions")
                ),
                "target_update_manager_decision_interactions": _int_value(
                    interaction_summary.get("target_update_manager_decision_interactions")
                ),
                "fake_provider_handoff_scenarios": _int_value(
                    fake_provider_summary.get("manager_handoff_scenario_count")
                ),
                "fake_provider_ambiguous_back_reference_scenarios": _int_value(
                    fake_provider_summary.get("ambiguous_back_reference_scenarios")
                ),
                "responder_allowed_fact_scenarios": _int_value(
                    responder_summary.get("scenario_count")
                ),
                "context_covered_capabilities": _int_value(
                    coverage_summary.get("covered_capability_count")
                ),
                "context_blocked_capabilities": _int_value(
                    coverage_summary.get("blocked_capability_count")
                ),
                "context_known_runtime_gaps": _int_value(
                    coverage_summary.get("known_runtime_gap_count")
                ),
                "session_pending_followup_carryover_checked": (
                    session_summary.get("pending_followup_carryover_checked") is True
                ),
                "session_target_candidate_ui_checked": (
                    session_summary.get("target_candidate_ui_checked") is True
                ),
                "session_long_context_checked": (
                    session_summary.get("long_session_pinned_draft_checked") is True
                ),
                "ui_chat_context_reload_checked": (
                    ui_summary.get("chat_context_reload_checked") is True
                ),
                "ui_today_seven_day_diary_checked": (
                    ui_summary.get("seven_day_diary_checked") is True
                ),
                "ui_body_read_model_checked": ui_summary.get("body_read_model_checked")
                is True,
            },
            "next_gate": {
                "name": "human_review_before_any_live_manager_intent_diagnostic",
                "ready_for_live_diagnostic_decision": False,
                "requires_fixed_case_matrix": True,
                "requires_anti_overfit_guard": True,
                "requires_human_approval": True,
                "fooddb_or_websearch_required": False,
            },
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "FORBIDDEN_TRUTHY_FLAGS",
    "REQUIRED_INPUTS",
    "build_manager_intent_readiness_review_pack_artifact",
]
