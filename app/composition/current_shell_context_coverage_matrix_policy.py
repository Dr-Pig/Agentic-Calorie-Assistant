from __future__ import annotations

from typing import Any

REQUIRED_INPUTS = (
    "context_conditioned_intent_wall",
    "short_term_context_runtime_replay",
    "fake_provider_context_smoke",
    "context_quality_pack",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_conditioned_intent_wall": "accurate_intake_context_conditioned_intent_wall",
    "short_term_context_runtime_replay": "accurate_intake_short_term_context_runtime_replay",
    "fake_provider_context_smoke": "accurate_intake_fake_provider_context_smoke",
    "context_quality_pack": "accurate_intake_context_quality_pack",
}

EXPECTED_STATUSES = {
    "context_conditioned_intent_wall": {"pass"},
    "short_term_context_runtime_replay": {
        "runtime_replay_diagnostic_pass",
        "diagnostic_has_known_context_gaps",
    },
    "fake_provider_context_smoke": {"pass"},
    "context_quality_pack": {"context_quality_diagnostic_pass"},
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
    "live_websearch_used",
    "websearch_evidence_used",
    "fooddb_evidence_used",
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


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "none", "null", "not_available", "not_checked"}
    return True


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload.get("summary")) if isinstance(payload.get("summary"), dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _input_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": payload.get("status") or "not_available",
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


def _nested_forbidden_claim_blockers(group_id: str, value: Any, path: str = "") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_TRUTHY_FLAGS and _claim_is_true(nested_value):
                blockers.append(f"{group_id}.{nested_path}")
            blockers.extend(_nested_forbidden_claim_blockers(group_id, nested_value, nested_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            blockers.extend(_nested_forbidden_claim_blockers(group_id, item, f"{path}[{index}]"))
    return list(dict.fromkeys(blockers))


def _upstream_invariant_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = _summary(payload)
    if group_id == "context_conditioned_intent_wall":
        if _int_value(summary.get("scenario_count")) < 11:
            blockers.append(f"{group_id}.scenario_count_too_low")
        if payload.get("manager_fixture_semantic_source_used") is not True:
            blockers.append(f"{group_id}.fixture_manager_semantic_source_missing")
    elif group_id == "short_term_context_runtime_replay":
        if payload.get("runtime_trace_backed") is not True:
            blockers.append(f"{group_id}.runtime_trace_backed_not_true")
        if _int_value(payload.get("scenario_count")) < 7:
            blockers.append(f"{group_id}.scenario_count_too_low")
    elif group_id == "fake_provider_context_smoke":
        if payload.get("manager_handoff_matrix_checked") is not True:
            blockers.append(f"{group_id}.manager_handoff_matrix_missing")
        scenario_count = _int_value(summary.get("manager_handoff_scenario_count"))
        actual_scenario_count = len(_list_value(payload.get("manager_handoff_scenarios")))
        if scenario_count != actual_scenario_count:
            blockers.append(f"{group_id}.manager_handoff_scenario_count_mismatch")
        if scenario_count < 6:
            blockers.append(f"{group_id}.manager_handoff_scenario_count_too_low")
        if _int_value(summary.get("ambiguous_back_reference_scenarios")) < 1:
            blockers.append(f"{group_id}.ambiguous_back_reference_missing")
    elif group_id == "context_quality_pack":
        if payload.get("short_term_context_runtime_replay_checked") is not True:
            blockers.append(f"{group_id}.runtime_replay_not_checked")
        if _int_value(summary.get("short_term_runtime_replay_scenario_count")) < 7:
            blockers.append(f"{group_id}.short_term_runtime_replay_scenario_count_too_low")
        if _int_value(summary.get("fake_provider_handoff_scenario_count")) < 6:
            blockers.append(f"{group_id}.fake_provider_handoff_scenario_count_too_low")
    return blockers


def _input_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
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
    blockers.extend(_nested_forbidden_claim_blockers(group_id, payload))
    blockers.extend(_upstream_invariant_blockers(group_id, payload))
    return list(dict.fromkeys(blockers))
