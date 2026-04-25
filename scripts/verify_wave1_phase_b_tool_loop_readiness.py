from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_readiness.json"
DEFAULT_PHASE_B_REPORT = ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_smoke.json"

REQUIRED_PROVIDER_PARAM_KEYS = (
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "response_format",
    "timeout",
    "retry_policy",
    "tool_choice",
    "request_id",
)
READ_PACKET_TRUTH_LEVELS = {"candidate", "hint", "rule_hint"}
PACKETIZER_TRUTH_LEVELS = {"candidate", "hint", "rule_hint"}
MUTATION_TRUTH_LEVEL = "mutation_result"
ESTIMATE_READ_TOOLS = {"lookup_generic_food", "retrieve_web_food_evidence"}
SUPPORTED_READ_TOOLS = {
    "lookup_generic_food",
    "retrieve_web_food_evidence",
    "load_taiwan_food_semantics_skill",
}
TAVILY_SOURCE_QUALITY_LABELS = {
    "official",
    "brand_menu",
    "trusted_database",
    "third_party",
    "irrelevant",
    "unknown",
}
REQUIRED_CORE_SMOKE_CASES = (
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "珍珠奶茶大概多少熱量？",
)
LOGGED_ESTIMABLE_CASES = {
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了豆干、海帶、貢丸的滷味",
}
NO_MUTATION_QUERY_CASES = {
    "珍珠奶茶大概多少熱量？",
}
EXPECTED_GENERIC_LOOKUP_CASES = LOGGED_ESTIMABLE_CASES | NO_MUTATION_QUERY_CASES
FORCED_MODE = "forced_tool_request_smoke"
NATURAL_MODE = "natural_tool_selection_probe"
FULL_SMOKE_LATENCY_TARGET_MS = 180_000
RUNTIME_LATENCY_REQUIRED_KEYS = (
    "latency_budget_type",
    "not_user_runtime_budget",
    "full_smoke_target_ms",
    "total_latency_ms",
    "trace_count",
    "completed_trace_count",
    "mode",
)
CASE_LATENCY_REQUIRED_KEYS = ("case_started_at_utc", "case_ended_at_utc", "case_latency_ms")
PASS_LATENCY_REQUIRED_KEYS = ("started_at_utc", "ended_at_utc", "latency_ms")
MANAGER_DECISION_TRACE_KEYS = ("decision_payload_type", "payload_shape_valid", "payload_shape_error")
LEGACY_PHASE_B_TERMS = (
    "thread_result",
    "target_thread_action",
    "clarify_mode",
    "commit_status",
    "canonical_commit",
)
DEFAULT_ACTIVE_PHASE_B_PATHS = (
    ROOT / "docs" / "specs" / "WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md",
    ROOT / "scripts" / "run_wave1_phase_b_minimal_tool_loop_smoke.py",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_path(path_text: str | None, *, default: Path) -> Path:
    if not path_text:
        return default
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _add(blockers: list[dict[str, str]], code: str, detail: str) -> None:
    blockers.append({"code": code, "detail": detail})


def _warn(warnings: list[dict[str, str]], code: str, detail: str) -> None:
    warnings.append({"code": code, "detail": detail})


def _has_value(mapping: dict[str, Any], key: str) -> bool:
    return key in mapping


def _provider_param_missing(params: Any) -> list[str]:
    if not isinstance(params, dict):
        return list(REQUIRED_PROVIDER_PARAM_KEYS)
    return [key for key in REQUIRED_PROVIDER_PARAM_KEYS if not _has_value(params, key)]


def _truth_level(value: Any) -> str | None:
    if isinstance(value, dict):
        raw = value.get("truth_level")
        return str(raw) if raw is not None else None
    return None


def _contains_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        return key_name in value or any(_contains_key(item, key_name) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key_name) for item in value)
    return False


def _scan_active_legacy_vocab(paths: list[Path], blockers: list[dict[str, str]], warnings: list[dict[str, str]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            allow_forbidden_list = (
                "LEGACY_PHASE_B_TERMS" in line
                or "Forbidden legacy terms" in line
                or "must not contain" in line
                or "不得" in line
                or "禁止" in line
            )
            for term in LEGACY_PHASE_B_TERMS:
                if term in line and not allow_forbidden_list:
                    findings.append(
                        {
                            "path": _project_relative(path),
                            "line": line_no,
                            "term": term,
                            "text": stripped,
                        }
                    )
    if findings:
        _add(
            blockers,
            "legacy_vocab_in_active_phase_b_surface",
            "Active Phase B-1 spec/code must not depend on legacy manager vocabulary.",
        )
    missing_paths = [_project_relative(path) for path in paths if not path.exists()]
    if missing_paths:
        _warn(
            warnings,
            "active_phase_b_paths_missing",
            f"Some active Phase B paths do not exist yet: {', '.join(missing_paths)}.",
        )
    return {"findings": findings, "missing_paths": missing_paths, "passed": not findings}


def _check_provider_params(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    for pass_name in ("manager_pass_1", "manager_pass_2"):
        params = (trace.get(pass_name) or {}).get("provider_params")
        pass_missing = _provider_param_missing(params)
        if pass_missing:
            missing[pass_name] = pass_missing
    if missing:
        _add(
            blockers,
            "provider_params_missing",
            f"Manager Pass 1/2 provider params must include {', '.join(REQUIRED_PROVIDER_PARAM_KEYS)}.",
        )
    return {"missing": missing, "passed": not missing}


def _check_pass_boundaries(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    pass_1_forbidden = list((trace.get("manager_pass_1") or {}).get("forbidden_final_truth_fields_present") or [])
    pass_2_mutation = bool((trace.get("manager_pass_2") or {}).get("mutation_attempted"))
    pass_2_forbidden_mutation_fields = list((trace.get("manager_pass_2") or {}).get("forbidden_mutation_fields_present") or [])
    if pass_1_forbidden:
        _add(blockers, "manager_pass_1_final_truth_present", "Manager Pass 1 must not contain final nutrition truth.")
    if pass_2_mutation:
        _add(blockers, "manager_pass_2_attempted_mutation", "Manager Pass 2 may synthesize item results but must not mutate.")
    if pass_2_forbidden_mutation_fields:
        _add(
            blockers,
            "manager_pass_2_forbidden_mutation_fields_present",
            "Manager Pass 2 must not output mutation_result, ledger_delta, or canonical_ledger_entry.",
        )
    return {
        "manager_pass_1_forbidden_fields": pass_1_forbidden,
        "manager_pass_2_mutation_attempted": pass_2_mutation,
        "manager_pass_2_forbidden_mutation_fields": pass_2_forbidden_mutation_fields,
        "passed": not pass_1_forbidden and not pass_2_mutation and not pass_2_forbidden_mutation_fields,
    }


def _check_manager_pass_prompt_trace(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    expected_roles = {
        "manager_pass_1": "pass_1_tool_request",
        "manager_pass_2": "pass_2_synthesis",
    }
    for pass_name, expected_role in expected_roles.items():
        payload = trace.get(pass_name) or {}
        pass_missing = [
            key
            for key in ("manager_round", "manager_role", "prompt_hash")
            if key not in payload or payload.get(key) in (None, "")
        ]
        if payload.get("manager_role") not in (None, expected_role):
            pass_missing.append("manager_role_expected_" + expected_role)
        if pass_missing:
            missing[pass_name] = pass_missing
    if missing:
        _add(
            blockers,
            "manager_pass_prompt_trace_missing",
            "Manager Pass 1/2 traces must include manager_round, manager_role, and prompt_hash.",
        )
    return {"missing": missing, "passed": not missing}


def _check_manager_payload_shape_trace(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    invalid: dict[str, dict[str, Any]] = {}
    for pass_name in ("manager_pass_1", "manager_pass_2"):
        payload = trace.get(pass_name) or {}
        pass_missing = [key for key in MANAGER_DECISION_TRACE_KEYS if key not in payload]
        if pass_missing:
            missing[pass_name] = pass_missing
            continue
        payload_shape_valid = payload.get("payload_shape_valid")
        payload_type = payload.get("decision_payload_type")
        payload_shape_error = payload.get("payload_shape_error")
        if payload_shape_valid is False:
            invalid[pass_name] = {
                "decision_payload_type": payload_type,
                "payload_shape_error": payload_shape_error,
            }
    if missing:
        _add(
            blockers,
            "manager_payload_shape_trace_missing",
            "Manager Pass 1/2 traces must include decision_payload_type, payload_shape_valid, and payload_shape_error.",
        )
    return {"missing": missing, "invalid": invalid, "passed": not missing}


def _check_tool_router_trace(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    router = trace.get("runtime_tool_router")
    executions = trace.get("read_tool_executions")
    ok = isinstance(router, dict) and isinstance(executions, list)
    if ok:
        ok = all(
            key in router
            for key in (
                "requested_read_tools",
                "allowed_tools",
                "filtered_tool_plan",
                "blocked_tools",
                "block_reasons",
                "available_read_tools",
                "canonical_tool_catalog_hash",
            )
        )
    if not ok:
        _add(blockers, "tool_router_trace_incomplete", "ToolLoopTrace must include requested tools, filtered plan, blocked tools, and read executions.")
    unsupported_allowed: list[str] = []
    unsupported_executed: list[str] = []
    unsupported_block_reason_missing: list[str] = []
    if isinstance(router, dict):
        allowed = [str(item) for item in router.get("allowed_tools") or []]
        supported = [str(item) for item in router.get("available_read_tools") or []]
        supported_set = set(supported) if supported else set(SUPPORTED_READ_TOOLS)
        unsupported_allowed = [tool for tool in allowed if tool not in supported_set]
        block_reasons = router.get("block_reasons") if isinstance(router.get("block_reasons"), list) else []
        blocked_unsupported = [
            str(item)
            for item in router.get("blocked_tools") or []
            if str(item) not in supported_set
        ]
        for tool_name in blocked_unsupported:
            matching = [
                reason
                for reason in block_reasons
                if isinstance(reason, dict)
                and reason.get("tool_name") == tool_name
                and reason.get("reason") == "unsupported_read_tool_name"
                and reason.get("normalization_attempted") is False
            ]
            if not matching:
                unsupported_block_reason_missing.append(tool_name)
        if not supported or not router.get("canonical_tool_catalog_hash"):
            _add(blockers, "canonical_tool_catalog_trace_missing", "Router trace must include supported read tools and a canonical tool catalog hash.")
    if isinstance(executions, list):
        unsupported_executed = [
            str(item.get("tool_name"))
            for item in executions
            if isinstance(item, dict) and str(item.get("tool_name")) not in SUPPORTED_READ_TOOLS
        ]
    if unsupported_allowed:
        _add(blockers, "unsupported_read_tool_allowed", "Runtime router must not allow non-canonical read tool names.")
    if unsupported_executed:
        _add(blockers, "unsupported_read_tool_executed", "Runtime router must not execute non-canonical read tool names.")
    if unsupported_block_reason_missing:
        _add(blockers, "unsupported_read_tool_block_reason_missing", "Blocked non-canonical read tools must include structured unsupported_read_tool_name reasons.")
    unknown_basket_check = _check_self_selected_basket_without_ingredients(trace, router if isinstance(router, dict) else {}, blockers)
    return {
        "passed": ok
        and not unsupported_allowed
        and not unsupported_executed
        and not unsupported_block_reason_missing
        and unknown_basket_check["passed"],
        "unsupported_allowed_tools": unsupported_allowed,
        "unsupported_executed_tools": unsupported_executed,
        "unsupported_block_reason_missing": unsupported_block_reason_missing,
        "self_selected_basket_without_ingredients": unknown_basket_check,
    }


def _is_self_selected_basket_without_ingredients(trace: dict[str, Any]) -> bool:
    marker = str(trace.get("semantic_boundary") or trace.get("family_boundary") or "")
    if marker == "self_selected_basket_without_ingredients":
        return True
    message = str(trace.get("input_message") or "")
    return message in {"我吃了滷味", "我吃滷味", "我吃了麻辣燙", "我吃麻辣燙"}


def _check_self_selected_basket_without_ingredients(
    trace: dict[str, Any],
    router: dict[str, Any],
    blockers: list[dict[str, str]],
) -> dict[str, Any]:
    if not _is_self_selected_basket_without_ingredients(trace):
        return {"checked": False, "passed": True}
    allowed = set(str(item) for item in router.get("allowed_tools") or [])
    filtered = set(str(item) for item in router.get("filtered_tool_plan") or [])
    blocked = set(str(item) for item in router.get("blocked_tools") or [])
    block_reasons = router.get("block_reasons") or []
    estimate_tools_allowed = sorted((allowed | filtered) & ESTIMATE_READ_TOOLS)
    estimate_tools_missing_from_blocked = sorted(ESTIMATE_READ_TOOLS - blocked)
    has_rule_reason = "self_selected_basket_without_ingredients_blocks_estimate_tools" in json.dumps(
        block_reasons,
        ensure_ascii=False,
    )
    passed = not estimate_tools_allowed and not estimate_tools_missing_from_blocked and has_rule_reason
    if not passed:
        _add(
            blockers,
            "self_selected_basket_without_ingredients_estimate_tools_not_blocked",
            "Self-selected basket without listed ingredients must block generic DB and Tavily estimate tools.",
        )
    return {
        "checked": True,
        "estimate_tools_allowed": estimate_tools_allowed,
        "estimate_tools_missing_from_blocked": estimate_tools_missing_from_blocked,
        "has_rule_reason": has_rule_reason,
        "passed": passed,
    }


def _check_truth_levels(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    invalid_read_outputs: list[dict[str, Any]] = []
    invalid_packet_outputs: list[dict[str, Any]] = []
    invalid_source_quality_labels: list[dict[str, Any]] = []
    for index, execution in enumerate(trace.get("read_tool_executions") or []):
        output = execution.get("output") if isinstance(execution, dict) else None
        level = _truth_level(output)
        if level not in READ_PACKET_TRUTH_LEVELS:
            invalid_read_outputs.append({"index": index, "truth_level": level})
    for index, packet in enumerate(((trace.get("packetizer") or {}).get("outputs") or [])):
        level = _truth_level(packet)
        if level not in PACKETIZER_TRUTH_LEVELS:
            invalid_packet_outputs.append({"index": index, "truth_level": level})
        if isinstance(packet, dict) and _contains_key(packet, "final_kcal"):
            invalid_packet_outputs.append({"index": index, "truth_level": level, "reason": "final_kcal_present"})
        if isinstance(packet, dict) and packet.get("packet_type") == "SearchCandidatePacket":
            label = packet.get("source_quality_label")
            if label not in TAVILY_SOURCE_QUALITY_LABELS:
                invalid_source_quality_labels.append({"index": index, "source_quality_label": label})
    if invalid_read_outputs:
        _add(blockers, "read_tool_truth_level_invalid", "Read tool outputs must use candidate/hint/rule_hint truth levels only.")
    if invalid_packet_outputs:
        _add(blockers, "packetizer_truth_level_invalid", "Packetizer outputs must remain candidate/hint/rule_hint and no final truth.")
    if invalid_source_quality_labels:
        _add(blockers, "tavily_source_quality_label_invalid", "SearchCandidatePacket source_quality_label must use the Phase B-1 enum.")
    return {
        "invalid_read_outputs": invalid_read_outputs,
        "invalid_packet_outputs": invalid_packet_outputs,
        "invalid_source_quality_labels": invalid_source_quality_labels,
        "mutation_truth_level": MUTATION_TRUTH_LEVEL,
        "passed": not invalid_read_outputs and not invalid_packet_outputs and not invalid_source_quality_labels,
    }


def _check_guard_and_mutation(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    guard = trace.get("guard") or {}
    mutation = trace.get("mutation") or {}
    guard_ok = bool(guard.get("ran")) and bool(guard.get("ran_before_mutation"))
    if not guard_ok:
        _add(blockers, "guard_not_run_before_mutation", "Deterministic guard must run before mutation.")
    mutation_keys_ok = all(key in mutation for key in ("mutation_attempted", "reason", "mutation_result"))
    if not mutation_keys_ok:
        _add(blockers, "mutation_trace_incomplete", "Mutation trace must always include mutation_attempted, reason, and mutation_result.")
    attempted = bool(mutation.get("mutation_attempted"))
    no_mutation_query_violation = (
        trace.get("input_message") == "珍珠奶茶大概多少熱量？"
        and attempted
    )
    if no_mutation_query_violation:
        _add(blockers, "no_mutation_query_mutated_ledger", "Nutrition info query may use read tools but must not mutate ledger.")
    input_message = str(trace.get("input_message") or "")
    no_mutation_shape_invalid = mutation_keys_ok and not attempted and mutation.get("mutation_result") is not None
    if mutation_keys_ok and not attempted and input_message in NO_MUTATION_QUERY_CASES and mutation.get("reason") != "no_mutation_intent":
        no_mutation_shape_invalid = True
    if no_mutation_shape_invalid:
        _add(blockers, "mutation_trace_incomplete", "No-mutation trace must use reason=no_mutation_intent and mutation_result=null.")
    return {
        "guard_ran_before_mutation": guard_ok,
        "mutation_trace_shape_valid": mutation_keys_ok and not no_mutation_shape_invalid,
        "no_mutation_query_violation": no_mutation_query_violation,
        "passed": guard_ok and mutation_keys_ok and not no_mutation_shape_invalid and not no_mutation_query_violation,
    }


def _has_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _quality_add(blockers: list[dict[str, str]], code: str, detail: str) -> None:
    blockers.append({"code": code, "detail": detail})


def _check_path_level_quality(trace: dict[str, Any], quality_blockers: list[dict[str, str]]) -> dict[str, Any]:
    input_message = str(trace.get("input_message") or "")
    manager_pass_1 = trace.get("manager_pass_1") or {}
    manager_pass_2 = trace.get("manager_pass_2") or {}
    router = trace.get("runtime_tool_router") or {}
    mutation = trace.get("mutation") or {}
    read_tool_executions = trace.get("read_tool_executions") or []
    packetizer_outputs = (trace.get("packetizer") or {}).get("outputs") or []
    item_results = manager_pass_2.get("item_results") or []
    pass2_params = manager_pass_2.get("provider_params") or {}

    failures: list[str] = []
    is_logged_estimable = input_message in LOGGED_ESTIMABLE_CASES
    is_query = input_message in NO_MUTATION_QUERY_CASES
    is_blocking_basket = _is_self_selected_basket_without_ingredients(trace)

    requested = list(manager_pass_1.get("requested_read_tools") or router.get("requested_read_tools") or [])
    allowed = list(router.get("allowed_tools") or [])

    if is_logged_estimable:
        if not requested:
            _quality_add(
                quality_blockers,
                "expected_tool_request_coverage_missing",
                "Logged estimable B-1 cases must have Manager Pass 1 read-tool requests.",
            )
            failures.append("expected_tool_request_coverage_missing")
        if not allowed:
            _quality_add(
                quality_blockers,
                "expected_tool_request_coverage_missing",
                "Logged estimable B-1 cases must have allowed read tools after router validation.",
            )
            failures.append("expected_allowed_tool_coverage_missing")
        if not _has_non_empty_list(read_tool_executions):
            _quality_add(
                quality_blockers,
                "expected_tool_execution_coverage_missing",
                "Logged estimable B-1 cases must execute deterministic read-tool fixtures.",
            )
            failures.append("expected_tool_execution_coverage_missing")
        if not _has_non_empty_list(packetizer_outputs):
            _quality_add(
                quality_blockers,
                "expected_packetizer_output_coverage_missing",
                "Logged estimable B-1 cases must produce packetizer outputs before Pass 2 synthesis.",
            )
            failures.append("expected_packetizer_output_coverage_missing")
        if not _has_non_empty_list(item_results):
            _quality_add(
                quality_blockers,
                "manager_pass2_item_results_missing",
                "Logged estimable B-1 cases require non-empty Manager Pass 2 item_results.",
            )
            failures.append("manager_pass2_item_results_missing")

    if is_query and not requested:
        _quality_add(
            quality_blockers,
            "query_answer_tool_support_missing",
            "Nutrition query B-1 case did not request read tools; scaffold may pass, but query-answer quality is not proven.",
        )
        failures.append("query_answer_tool_support_missing")

    if is_blocking_basket:
        estimate_executions = [
            item for item in read_tool_executions
            if isinstance(item, dict) and str(item.get("tool_name") or "") in ESTIMATE_READ_TOOLS
        ]
        estimate_packets = [
            packet for packet in packetizer_outputs
            if isinstance(packet, dict) and packet.get("packet_type") in {"GenericFoodDbPacket", "SearchCandidatePacket"}
        ]
        if estimate_executions or estimate_packets:
            _quality_add(
                quality_blockers,
                "blocking_case_estimate_path_executed",
                "Self-selected basket without ingredients must not execute or packetize estimate tools.",
            )
            failures.append("blocking_case_estimate_path_executed")

    if bool(mutation.get("mutation_attempted")) and not _has_non_empty_list(item_results):
        _quality_add(
            quality_blockers,
            "mutation_without_item_results",
            "Ledger mutation requires non-empty Manager Pass 2 item_results; mutation cannot be approved from intent alone.",
        )
        failures.append("mutation_without_item_results")

    missing_pass2_values = [
        key for key in ("provider", "model", "request_id")
        if not isinstance(pass2_params, dict) or pass2_params.get(key) in (None, "")
    ]
    if missing_pass2_values:
        _quality_add(
            quality_blockers,
            "pass2_provider_trace_missing",
            "Manager Pass 2 provider/model/request_id trace must be present to prove a real second LLM pass.",
        )
        failures.append("pass2_provider_trace_missing")

    return {
        "input_message": input_message,
        "is_logged_estimable": is_logged_estimable,
        "is_no_mutation_query": is_query,
        "is_blocking_basket": is_blocking_basket,
        "requested_read_tools": requested,
        "allowed_tools": allowed,
        "read_tool_execution_count": len(read_tool_executions) if isinstance(read_tool_executions, list) else 0,
        "packetizer_output_count": len(packetizer_outputs) if isinstance(packetizer_outputs, list) else 0,
        "item_result_count": len(item_results) if isinstance(item_results, list) else 0,
        "mutation_attempted": bool(mutation.get("mutation_attempted")),
        "missing_pass2_provider_values": missing_pass2_values,
        "failures": failures,
        "passed": not failures,
    }


def _trace_requested_allowed(trace: dict[str, Any]) -> tuple[list[str], list[str]]:
    manager_pass_1 = trace.get("manager_pass_1") or {}
    router = trace.get("runtime_tool_router") or {}
    requested = list(manager_pass_1.get("requested_read_tools") or router.get("requested_read_tools") or [])
    allowed = list(router.get("allowed_tools") or [])
    return [str(item) for item in requested], [str(item) for item in allowed]


def _has_estimate_execution_or_packet(trace: dict[str, Any]) -> bool:
    read_tool_executions = trace.get("read_tool_executions") or []
    packetizer_outputs = (trace.get("packetizer") or {}).get("outputs") or []
    estimate_executions = [
        item for item in read_tool_executions
        if isinstance(item, dict) and str(item.get("tool_name") or "") in ESTIMATE_READ_TOOLS
    ]
    estimate_packets = [
        packet for packet in packetizer_outputs
        if isinstance(packet, dict) and packet.get("packet_type") in {"GenericFoodDbPacket", "SearchCandidatePacket"}
    ]
    return bool(estimate_executions or estimate_packets)


def _expected_tool_policy_for_trace(trace: dict[str, Any]) -> dict[str, Any]:
    input_message = str(trace.get("input_message") or "")
    if _is_self_selected_basket_without_ingredients(trace):
        return {
            "policy_type": "self_selected_basket_without_ingredients",
            "required_tools": [],
            "lookup_generic_food": "not_required",
            "retrieve_web_food_evidence": "not_required",
            "estimate_tool_execution": "forbidden",
            "acceptable_paths": [
                "no_tool_request_with_blocking_semantics",
                "requested_estimate_tools_but_router_blocked",
            ],
        }
    if input_message in EXPECTED_GENERIC_LOOKUP_CASES:
        return {
            "policy_type": "generic_lookup_required",
            "required_tools": ["lookup_generic_food"],
            "optional_tools": ["retrieve_web_food_evidence"],
            "estimate_tool_execution": "allowed",
        }
    return {
        "policy_type": "not_applicable",
        "required_tools": [],
        "optional_tools": [],
    }


def _item_results_source(trace: dict[str, Any]) -> str:
    manager_pass_2 = trace.get("manager_pass_2") if isinstance(trace.get("manager_pass_2"), dict) else {}
    item_results = manager_pass_2.get("item_results") if isinstance(manager_pass_2, dict) else []
    if bool(trace.get("runner_derived_item_results")):
        return "runner_packet_fallback"
    if _has_non_empty_list(item_results):
        return "manager_pass_2_payload"
    return "none"


def _unsupported_tool_names(trace: dict[str, Any]) -> list[str]:
    router = trace.get("runtime_tool_router") if isinstance(trace.get("runtime_tool_router"), dict) else {}
    block_reasons = router.get("block_reasons") if isinstance(router, dict) else []
    unsupported: list[str] = []
    if isinstance(block_reasons, list):
        for reason in block_reasons:
            if isinstance(reason, dict) and reason.get("reason") == "unsupported_read_tool_name":
                tool_name = str(reason.get("tool_name") or "")
                if tool_name:
                    unsupported.append(tool_name)
    return sorted(set(unsupported))


def _natural_failure_family(
    *,
    trace: dict[str, Any],
    expected_policy: dict[str, Any],
    requested: list[str],
    allowed: list[str],
    missing_required: list[str],
    wrong_tools: list[str],
) -> str:
    if expected_policy.get("policy_type") == "self_selected_basket_without_ingredients":
        return "blocking_boundary_ok" if not _has_estimate_execution_or_packet(trace) else "router_policy_failure"
    if not requested and missing_required:
        return "manager_no_tool_request"
    if missing_required or wrong_tools:
        return "wrong_tool_request"
    manager_pass_2 = trace.get("manager_pass_2") if isinstance(trace.get("manager_pass_2"), dict) else {}
    pass2_params = manager_pass_2.get("provider_params") if isinstance(manager_pass_2, dict) else {}
    pass2_ran = isinstance(pass2_params, dict) and all(pass2_params.get(key) not in (None, "") for key in ("provider", "model", "request_id"))
    if not pass2_ran:
        return "pass2_not_run"
    if _item_results_source(trace) == "none":
        return "pass2_no_item_results"
    return "none"


def _build_natural_probe_failure_report(
    traces: list[dict[str, Any]],
    *,
    provider_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    counts: dict[str, int] = {
        "manager_no_tool_request": 0,
        "wrong_tool_request": 0,
        "router_policy_failure": 0,
        "pass2_not_run": 0,
        "pass2_no_item_results": 0,
        "blocking_boundary_ok": 0,
        "manager_blocking_semantics_not_proven": 0,
    }
    for trace in traces:
        requested, allowed = _trace_requested_allowed(trace)
        expected_policy = _expected_tool_policy_for_trace(trace)
        required_tools = [str(tool) for tool in expected_policy.get("required_tools") or []]
        optional_tools = set(str(tool) for tool in expected_policy.get("optional_tools") or [])
        missing_required = [tool for tool in required_tools if tool not in requested or tool not in allowed]
        wrong_tools = [
            tool for tool in requested
            if required_tools and (tool not in set(required_tools) | optional_tools or missing_required)
        ]
        manager_pass_2 = trace.get("manager_pass_2") if isinstance(trace.get("manager_pass_2"), dict) else {}
        pass2_params = manager_pass_2.get("provider_params") if isinstance(manager_pass_2, dict) else {}
        pass2_ran = isinstance(pass2_params, dict) and all(pass2_params.get(key) not in (None, "") for key in ("provider", "model", "request_id"))
        family = _natural_failure_family(
            trace=trace,
            expected_policy=expected_policy,
            requested=requested,
            allowed=allowed,
            missing_required=missing_required,
            wrong_tools=wrong_tools,
        )
        if family in counts:
            counts[family] += 1
        manager_blocking_semantics = "not_applicable"
        if expected_policy.get("policy_type") == "self_selected_basket_without_ingredients":
            # In B-1 natural-probe, no estimate execution proves the boundary, but
            # the current artifact does not yet prove the Manager itself selected
            # blocking semantics unless it emits explicit semantic state later.
            manager_blocking_semantics = "not_proven"
            counts["manager_blocking_semantics_not_proven"] += 1
        cases.append(
            {
                "case_id": trace.get("case_id"),
                "input_message": trace.get("input_message"),
                "expected_tool_policy": expected_policy,
                "actual_requested_read_tools": requested,
                "actual_allowed_tools": allowed,
                "missing_or_wrong_tools": {
                    "missing_required_tools": missing_required,
                    "wrong_tools": wrong_tools,
                },
                "unsupported_tool_names": _unsupported_tool_names(trace),
                "pass2_ran": pass2_ran,
                "item_results_source": _item_results_source(trace),
                "failure_family": family,
                "manager_blocking_semantics": manager_blocking_semantics,
            }
        )
    provider_state = provider_state or {}
    return {
        "cases": cases,
        "failure_family_counts": counts,
        "provider_blocked_before_cases": bool(provider_state.get("provider_blocked_before_cases")),
        "provider_blocked_before_all_cases_completed": bool(
            provider_state.get("provider_blocked_before_all_cases_completed")
        ),
        "completed_trace_count": provider_state.get("completed_trace_count", len(traces)),
        "expected_case_count": provider_state.get("expected_case_count", _expected_case_count()),
        "provider_runtime_reason": provider_state.get("provider_runtime_reason"),
    }


def _completed_trace_count(report: dict[str, Any], traces: list[dict[str, Any]]) -> int:
    runtime_latency = report.get("runtime_latency") if isinstance(report.get("runtime_latency"), dict) else {}
    raw_count = runtime_latency.get("completed_trace_count") if isinstance(runtime_latency, dict) else None
    if isinstance(raw_count, int):
        return min(raw_count, len(traces))
    return len(traces)


def _expected_case_count() -> int:
    return len(REQUIRED_CORE_SMOKE_CASES)


def _provider_blocker_state(report: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, Any]:
    provider_runtime = report.get("provider_runtime") if isinstance(report.get("provider_runtime"), dict) else {}
    runtime_blocker = report.get("runtime_blocker") if isinstance(report.get("runtime_blocker"), dict) else {}
    completed_count = _completed_trace_count(report, traces)
    expected_count = _expected_case_count()
    provider_blocker = bool(provider_runtime.get("blocker"))
    runtime_blocker_active = bool(runtime_blocker.get("blocker"))
    blocker_reason = runtime_blocker.get("reason") or provider_runtime.get("reason")
    blocker_kind = "runtime_blocker" if runtime_blocker_active else "provider_runtime" if provider_blocker else None
    any_blocker = provider_blocker or runtime_blocker_active
    return {
        "provider_blocker": provider_blocker,
        "runtime_blocker": runtime_blocker_active,
        "provider_runtime_reason": blocker_reason,
        "blocker_kind": blocker_kind,
        "completed_trace_count": completed_count,
        "expected_case_count": expected_count,
        "provider_blocked_before_cases": any_blocker and completed_count == 0,
        "provider_blocked_before_all_cases_completed": any_blocker and completed_count < expected_count,
    }


def _check_mode_verdicts(
    report: dict[str, Any],
    traces: list[dict[str, Any]],
    quality_blockers: list[dict[str, str]],
) -> dict[str, Any]:
    pass1_mode = str(report.get("pass1_mode") or FORCED_MODE)
    forced_contract = bool(report.get("forced_tool_request_contract"))
    manager_tool_selection_claimed = bool(report.get("manager_tool_selection_claimed"))
    reported_natural_pass = report.get("natural_tool_selection_pass")

    mode_failures: list[str] = []
    selection_failures: list[dict[str, Any]] = []
    loop_failures: list[dict[str, Any]] = []

    if pass1_mode == FORCED_MODE:
        if manager_tool_selection_claimed or reported_natural_pass is True:
            _quality_add(
                quality_blockers,
                "forced_mode_claimed_natural_tool_selection",
                "Forced tool-request smoke must not claim natural Manager tool-selection quality.",
            )
            mode_failures.append("forced_mode_claimed_natural_tool_selection")
        return {
            "pass1_mode": pass1_mode,
            "forced_loop_scaffold_pass": None,
            "natural_tool_selection_pass": "not_applicable",
            "natural_tool_loop_completion_pass": "not_applicable",
            "mode_failures": mode_failures,
            "selection_failures": selection_failures,
            "loop_failures": loop_failures,
        }

    if pass1_mode != NATURAL_MODE:
        _quality_add(quality_blockers, "unknown_pass1_mode", "Phase B-1 report must declare forced or natural-probe pass1_mode.")
        mode_failures.append("unknown_pass1_mode")
        return {
            "pass1_mode": pass1_mode,
            "forced_loop_scaffold_pass": None,
            "natural_tool_selection_pass": False,
            "natural_tool_loop_completion_pass": False,
            "mode_failures": mode_failures,
            "selection_failures": selection_failures,
            "loop_failures": loop_failures,
        }

    if forced_contract:
        _quality_add(quality_blockers, "natural_probe_used_forced_contract", "Natural probe must not use the forced call-tools contract.")
        mode_failures.append("natural_probe_used_forced_contract")
    if not manager_tool_selection_claimed:
        _quality_add(quality_blockers, "natural_probe_missing_tool_selection_claim", "Natural probe must explicitly claim it is evaluating Manager tool selection.")
        mode_failures.append("natural_probe_missing_tool_selection_claim")

    provider_state = _provider_blocker_state(report, traces)
    if provider_state["provider_blocked_before_cases"]:
        return {
            "pass1_mode": pass1_mode,
            "forced_loop_scaffold_pass": "not_applicable",
            "natural_tool_selection_pass": "not_proven",
            "natural_tool_loop_completion_pass": False,
            "mode_failures": mode_failures,
            "selection_failures": [
                {
                    "reason": "provider_blocked_before_cases",
                    "provider_runtime_reason": provider_state["provider_runtime_reason"],
                }
            ],
            "loop_failures": [
                {
                    "reason": "provider_blocked_before_cases",
                    "provider_runtime_reason": provider_state["provider_runtime_reason"],
                }
            ],
        }

    for trace in traces:
        input_message = str(trace.get("input_message") or "")
        requested, allowed = _trace_requested_allowed(trace)
        if input_message in EXPECTED_GENERIC_LOOKUP_CASES:
            if "lookup_generic_food" not in requested or "lookup_generic_food" not in allowed:
                selection_failures.append(
                    {
                        "case_id": trace.get("case_id"),
                        "input_message": input_message,
                        "expected_tool": "lookup_generic_food",
                        "requested_read_tools": requested,
                        "allowed_tools": allowed,
                    }
                )
        if _is_self_selected_basket_without_ingredients(trace):
            router = trace.get("runtime_tool_router") or {}
            blocked_check: list[dict[str, str]] = []
            block_result = _check_self_selected_basket_without_ingredients(trace, router if isinstance(router, dict) else {}, blocked_check)
            if not block_result.get("passed") or _has_estimate_execution_or_packet(trace):
                selection_failures.append(
                    {
                        "case_id": trace.get("case_id"),
                        "input_message": input_message,
                        "expected": "blocked_estimate_tools_without_estimate_execution",
                    }
                )

        manager_pass_2 = trace.get("manager_pass_2") or {}
        item_results = manager_pass_2.get("item_results") or []
        pass2_params = manager_pass_2.get("provider_params") or {}
        if input_message in LOGGED_ESTIMABLE_CASES and not _has_non_empty_list(item_results):
            loop_failures.append({"case_id": trace.get("case_id"), "input_message": input_message, "reason": "manager_pass2_item_results_missing"})
        missing_pass2_values = [
            key for key in ("provider", "model", "request_id")
            if not isinstance(pass2_params, dict) or pass2_params.get(key) in (None, "")
        ]
        if missing_pass2_values:
            loop_failures.append({"case_id": trace.get("case_id"), "input_message": input_message, "reason": "pass2_provider_trace_missing", "missing": missing_pass2_values})
        if bool(trace.get("runner_derived_item_results")):
            loop_failures.append({"case_id": trace.get("case_id"), "input_message": input_message, "reason": "natural_probe_runner_derived_item_results"})

    if selection_failures:
        _quality_add(
            quality_blockers,
            "expected_tool_policy_mismatch",
            "Natural-probe tool selection must request/allow the expected tool policy, not just any tool.",
        )
    if any(item.get("reason") == "natural_probe_runner_derived_item_results" for item in loop_failures):
        _quality_add(
            quality_blockers,
            "natural_probe_runner_derived_item_results",
            "Natural-probe item_results must come from Manager Pass 2, not runner packet fallback.",
        )

    natural_selection_pass: bool | str = not mode_failures and not selection_failures
    natural_loop_completion_pass = not mode_failures and not loop_failures
    if provider_state["provider_blocked_before_all_cases_completed"]:
        natural_selection_pass = "not_proven"
        natural_loop_completion_pass = False
        loop_failures.append(
            {
                "reason": "provider_blocked_before_all_cases_completed",
                "completed_trace_count": provider_state["completed_trace_count"],
                "expected_case_count": provider_state["expected_case_count"],
                "provider_runtime_reason": provider_state["provider_runtime_reason"],
            }
        )

    return {
        "pass1_mode": pass1_mode,
        "forced_loop_scaffold_pass": "not_applicable",
        "natural_tool_selection_pass": natural_selection_pass,
        "natural_tool_loop_completion_pass": natural_loop_completion_pass,
        "mode_failures": mode_failures,
        "selection_failures": selection_failures,
        "loop_failures": loop_failures,
    }


def _check_renderer_boundary(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    renderer = trace.get("renderer") or {}
    invented = list(renderer.get("invented_facts") or [])
    renderer_input = renderer.get("input")
    input_present = isinstance(renderer_input, dict)
    required_input_keys = ("allowed_facts", "forbidden_claims", "item_results", "ledger_mutation_result")
    missing_input_keys = [
        key for key in required_input_keys if not input_present or key not in renderer_input
    ]
    final_response = str(renderer.get("final_response") or "")
    allowed_text = json.dumps(renderer_input or {}, ensure_ascii=False)
    response_has_unbacked_claim = bool(final_response) and any(
        marker in final_response and marker not in allowed_text
        for marker in ("大卡", "還剩", "已記錄", "logged", "remaining")
    )
    if response_has_unbacked_claim:
        invented.append("final_response_contains_fact_outside_renderer_input")
    if not input_present or missing_input_keys or invented:
        _add(blockers, "renderer_truth_boundary_failed", "Renderer must receive truth input and must not invent facts.")
    return {
        "invented_facts": invented,
        "input_present": input_present,
        "missing_input_keys": missing_input_keys,
        "passed": input_present and not missing_input_keys and not invented,
    }


def _check_stub_fixture(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    if trace.get("is_live_tavily_canary"):
        return {"checked": False, "passed": True}
    deterministic = bool(trace.get("uses_deterministic_stub_fixtures"))
    generated_by_llm = bool(trace.get("stub_generated_by_llm"))
    source = trace.get("stub_fixture_source")
    packet_metadata_missing: list[int] = []
    for index, packet in enumerate(((trace.get("packetizer") or {}).get("outputs") or [])):
        if not isinstance(packet, dict):
            packet_metadata_missing.append(index)
            continue
        required = ("fixture_id", "fixture_hash", "fixture_only", "generated_by")
        if any(key not in packet for key in required) or packet.get("fixture_only") is not True or packet.get("generated_by") != "deterministic_fixture":
            packet_metadata_missing.append(index)
    if packet_metadata_missing:
        _add(
            blockers,
            "packetizer_fixture_metadata_missing",
            "Core stub packetizer outputs must include fixture_id, fixture_hash, fixture_only=true, and generated_by=deterministic_fixture.",
        )
    if not deterministic or generated_by_llm or not source:
        _add(blockers, "stub_fixture_generated_by_llm", "Core Phase B-1 stub packets must be deterministic fixtures, not LLM-generated.")
    return {
        "checked": True,
        "uses_deterministic_stub_fixtures": deterministic,
        "stub_generated_by_llm": generated_by_llm,
        "stub_fixture_source": source,
        "packet_metadata_missing": packet_metadata_missing,
        "passed": deterministic and not generated_by_llm and bool(source) and not packet_metadata_missing,
    }


def _check_tavily_canary(trace: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    if not trace.get("is_live_tavily_canary"):
        return {"checked": False, "passed": True}
    canary = trace.get("tavily_canary") or {}
    mutation = trace.get("mutation") or {}
    required = (
        "query",
        "search_depth",
        "max_results",
        "chunks_per_source",
        "provider_params",
        "raw_results_ref",
        "latency_ms",
        "call_count",
    )
    missing = [key for key in required if key not in canary]
    if not bool(canary.get("packetized_candidate_present")):
        missing.append("packetized_candidate_present")
    if not bool(canary.get("manager_pass_2_saw_search_packet")):
        missing.append("manager_pass_2_saw_search_packet")
    if missing:
        _add(blockers, "tavily_canary_trace_incomplete", "Live Tavily canary must trace query, params, raw output ref, packet, latency, and Pass 2 usage.")
    mutated = bool(mutation.get("mutation_attempted"))
    if mutated:
        _add(blockers, "tavily_canary_mutated_ledger", "Live Tavily canary must not create ledger mutation in Phase B-1.")
    return {"missing": missing, "mutated_ledger": mutated, "passed": not missing and not mutated}


def _check_core_smoke_cases(report: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    cases_run = set(str(item) for item in report.get("core_smoke_cases_run") or [])
    missing = [case for case in REQUIRED_CORE_SMOKE_CASES if case not in cases_run]
    if missing:
        _add(blockers, "core_smoke_case_missing", f"Missing Phase B-1 core smoke cases: {', '.join(missing)}.")
    return {"required": list(REQUIRED_CORE_SMOKE_CASES), "missing": missing, "passed": not missing}


def _missing_keys(payload: Any, keys: tuple[str, ...]) -> list[str]:
    if not isinstance(payload, dict):
        return list(keys)
    return [key for key in keys if key not in payload or payload.get(key) in (None, "")]


def _check_runtime_latency(
    report: dict[str, Any],
    traces: list[dict[str, Any]],
    latency_blockers: list[dict[str, str]],
    latency_warnings: list[dict[str, str]],
) -> dict[str, Any]:
    provider_runtime = report.get("provider_runtime") if isinstance(report.get("provider_runtime"), dict) else {}
    runtime_latency = report.get("runtime_latency") if isinstance(report.get("runtime_latency"), dict) else {}
    missing: dict[str, Any] = {}

    if provider_runtime.get("reason") == "provider_timeout":
        _add(
            latency_blockers,
            "provider_timeout",
            "Provider timeout must block readiness and be represented in provider_runtime.",
        )

    top_missing = _missing_keys(runtime_latency, RUNTIME_LATENCY_REQUIRED_KEYS)
    if top_missing:
        missing["runtime_latency"] = top_missing

    trace_missing: list[dict[str, Any]] = []
    for trace in traces:
        case_missing = _missing_keys(trace, CASE_LATENCY_REQUIRED_KEYS)
        pass_missing: dict[str, list[str]] = {}
        for pass_name in ("manager_pass_1", "manager_pass_2"):
            payload = trace.get(pass_name) if isinstance(trace.get(pass_name), dict) else {}
            missing_pass_keys = _missing_keys(payload, PASS_LATENCY_REQUIRED_KEYS)
            if missing_pass_keys:
                pass_missing[pass_name] = missing_pass_keys
        if case_missing or pass_missing:
            trace_missing.append(
                {
                    "case_id": trace.get("case_id"),
                    "case_missing": case_missing,
                    "pass_missing": pass_missing,
                }
            )
    if trace_missing:
        missing["tool_loop_traces"] = trace_missing

    if missing:
        _add(
            latency_blockers,
            "runtime_latency_trace_missing",
            "B-1 latency gate requires total, case-level, and pass-level latency fields.",
        )

    total_latency_ms = runtime_latency.get("total_latency_ms") if isinstance(runtime_latency, dict) else None
    target_ms = runtime_latency.get("full_smoke_target_ms", FULL_SMOKE_LATENCY_TARGET_MS) if isinstance(runtime_latency, dict) else FULL_SMOKE_LATENCY_TARGET_MS
    over_target = (
        isinstance(total_latency_ms, (int, float))
        and isinstance(target_ms, (int, float))
        and total_latency_ms > target_ms
    )
    if over_target and not missing and provider_runtime.get("reason") != "provider_timeout":
        _warn(
            latency_warnings,
            "runtime_latency_over_target",
            "B-1 full smoke latency exceeded reporting target; this is a warning, not a truth-boundary failure.",
        )

    status = "blocker" if latency_blockers else "warning" if latency_warnings else "pass"
    return {
        "status": status,
        "pass": status == "pass",
        "target_ms": target_ms,
        "total_latency_ms": total_latency_ms,
        "latency_budget_type": runtime_latency.get("latency_budget_type") if isinstance(runtime_latency, dict) else None,
        "not_user_runtime_budget": runtime_latency.get("not_user_runtime_budget") if isinstance(runtime_latency, dict) else None,
        "missing": missing,
        "over_target": over_target,
    }


def verify_phase_b_readiness(
    *,
    phase_b_report_path: Path,
    active_paths: list[Path] | None = None,
) -> dict[str, Any]:
    phase_b_report = _read_json(phase_b_report_path)
    blockers: list[dict[str, str]] = []
    quality_blockers: list[dict[str, str]] = []
    latency_blockers: list[dict[str, str]] = []
    latency_warnings: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    traces = [dict(item) for item in phase_b_report.get("tool_loop_traces") or []]
    provider_state = _provider_blocker_state(phase_b_report, traces)

    if phase_b_report.get("mode") != "hybrid_canary":
        _add(blockers, "phase_b_mode_not_hybrid_canary", "Phase B-1 readiness requires hybrid_canary mode.")
    if provider_state["provider_blocker"]:
        _add(
            blockers,
            "provider_runtime_blocker",
            "Provider runtime blocker prevents B-1 readiness from proving tool-loop quality.",
        )
    if provider_state["runtime_blocker"]:
        _add(
            blockers,
            "manager_payload_shape_error",
            "Manager payload shape blocker prevents B-1 readiness from proving tool-loop quality.",
        )
    if not traces:
        _add(blockers, "tool_loop_trace_missing", "Phase B-1 readiness requires ToolLoopTrace artifacts.")

    core_smoke_cases = _check_core_smoke_cases(phase_b_report, blockers)
    runtime_latency = _check_runtime_latency(phase_b_report, traces, latency_blockers, latency_warnings)
    trace_checks: list[dict[str, Any]] = []
    for trace in traces:
        trace_blockers_before = len(blockers)
        checks = {
            "case_id": trace.get("case_id"),
            "provider_params": _check_provider_params(trace, blockers),
            "manager_pass_prompt_trace": _check_manager_pass_prompt_trace(trace, blockers),
            "manager_payload_shape_trace": _check_manager_payload_shape_trace(trace, blockers),
            "pass_boundaries": _check_pass_boundaries(trace, blockers),
            "tool_router_trace": _check_tool_router_trace(trace, blockers),
            "truth_levels": _check_truth_levels(trace, blockers),
            "guard_and_mutation": _check_guard_and_mutation(trace, blockers),
            "renderer_boundary": _check_renderer_boundary(trace, blockers),
            "stub_fixture": _check_stub_fixture(trace, blockers),
            "tavily_canary": _check_tavily_canary(trace, blockers),
        }
        checks["passed"] = len(blockers) == trace_blockers_before
        trace_checks.append(checks)
    router_validation_pass = bool(traces) and all(
        bool((check.get("tool_router_trace") or {}).get("passed"))
        for check in trace_checks
    )

    resolved_active_paths = list(active_paths) if active_paths is not None else list(DEFAULT_ACTIVE_PHASE_B_PATHS)
    legacy_vocab = _scan_active_legacy_vocab(resolved_active_paths, blockers, warnings)

    scaffold_pass = not blockers
    path_level_quality = [_check_path_level_quality(trace, quality_blockers) for trace in traces]
    mode_verdicts = _check_mode_verdicts(phase_b_report, traces, quality_blockers)
    natural_probe_failure_report = (
        _build_natural_probe_failure_report(traces, provider_state=provider_state)
        if mode_verdicts["pass1_mode"] == NATURAL_MODE
        else {"cases": [], "failure_family_counts": {}}
    )
    if mode_verdicts["pass1_mode"] == FORCED_MODE:
        forced_loop_scaffold_pass = scaffold_pass and not quality_blockers
        mode_verdicts["forced_loop_scaffold_pass"] = forced_loop_scaffold_pass
        natural_tool_selection_pass: bool | str = "not_applicable"
        natural_tool_loop_completion_pass: bool | str = "not_applicable"
        quality_pass = forced_loop_scaffold_pass
    else:
        forced_loop_scaffold_pass = "not_applicable"
        raw_selection_pass = mode_verdicts["natural_tool_selection_pass"]
        natural_tool_selection_pass = "not_proven" if raw_selection_pass == "not_proven" else bool(raw_selection_pass)
        natural_tool_loop_completion_pass = bool(mode_verdicts["natural_tool_loop_completion_pass"])
        quality_pass = (
            scaffold_pass
            and natural_tool_selection_pass is True
            and natural_tool_loop_completion_pass
            and not quality_blockers
        )
    provider_runtime = phase_b_report.get("provider_runtime") if isinstance(phase_b_report.get("provider_runtime"), dict) else {}
    runtime_blocker = phase_b_report.get("runtime_blocker") if isinstance(phase_b_report.get("runtime_blocker"), dict) else {}
    provider_runtime_attribution = {
        "reason": runtime_blocker.get("reason") or provider_runtime.get("reason"),
        "blocker_kind": provider_state.get("blocker_kind"),
        "tool_selection_status": "not_proven" if provider_state["provider_blocked_before_all_cases_completed"] else "evaluated",
        "loop_completion_status": "blocked" if provider_state["provider_blocked_before_all_cases_completed"] else "evaluated",
    }
    all_blockers = blockers + quality_blockers + latency_blockers
    ready = not all_blockers
    blocker_codes = {item["code"] for item in all_blockers}
    if ready:
        next_steps = ["proceed_to_phase_b1_minimal_tool_loop_implementation"]
    else:
        next_steps = []
        if "expected_tool_request_coverage_missing" in blocker_codes:
            next_steps.append("tighten_manager_pass1_tool_request_contract")
        if "pass2_provider_trace_missing" in blocker_codes:
            next_steps.append("ensure_manager_pass2_runs_after_packetized_tool_results")
        if "mutation_without_item_results" in blocker_codes:
            next_steps.append("harden_guard_no_mutation_without_item_results")
        next_steps.extend(["rerun_phase_b1_runtime_smoke", "rerun_phase_b1_readiness_gate"])

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "phase_b_report_path": _project_relative(phase_b_report_path),
        "scaffold_pass": scaffold_pass,
        "forced_loop_scaffold_pass": forced_loop_scaffold_pass,
        "router_validation_pass": router_validation_pass,
        "natural_tool_selection_pass": natural_tool_selection_pass,
        "natural_tool_loop_completion_pass": natural_tool_loop_completion_pass,
        "runtime_latency_pass": runtime_latency["pass"],
        "runtime_latency_status": runtime_latency["status"],
        "quality_pass": quality_pass,
        "provider_runtime_attribution": provider_runtime_attribution,
        "runtime_blocker": runtime_blocker,
        "ready_for_phase_b1_implementation": ready,
        "blockers": all_blockers,
        "scaffold_blockers": blockers,
        "quality_blockers": quality_blockers,
        "latency_blockers": latency_blockers,
        "latency_warnings": latency_warnings,
        "warnings": warnings,
        "runtime_latency": runtime_latency,
        "natural_probe_failure_report": natural_probe_failure_report,
        "core_smoke_cases": core_smoke_cases,
        "trace_checks": trace_checks,
        "path_level_quality": path_level_quality,
        "mode_verdicts": mode_verdicts,
        "legacy_adjacency_check": legacy_vocab,
        "recommended_next_steps_ordered": (
            next_steps
        ),
    }
    return _json_safe(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Wave 1 Phase B-1 minimal tool-loop readiness.")
    parser.add_argument("--phase-b-report", default=str(DEFAULT_PHASE_B_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    phase_b_report_path = _resolve_path(args.phase_b_report, default=DEFAULT_PHASE_B_REPORT)
    output_path = _resolve_path(args.output, default=DEFAULT_OUTPUT)
    report = verify_phase_b_readiness(phase_b_report_path=phase_b_report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(output_path),
                "ready_for_phase_b1_implementation": report["ready_for_phase_b1_implementation"],
                "blocker_count": len(report["blockers"]),
                "recommended_next_steps_ordered": report["recommended_next_steps_ordered"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready_for_phase_b1_implementation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
