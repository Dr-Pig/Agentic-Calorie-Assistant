from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wave1_phase_b2_live_llm_diagnostic_canary import build_provider_request_payload_for_case

DEFAULT_PHASE_B2_REPORT = ROOT / "artifacts" / "wave1_phase_b2_evidence_synthesis_smoke.json"
DEFAULT_LIVE_REPORT = ROOT / "artifacts" / "wave1_phase_b2_live_llm_diagnostic_canary.json"
DEFAULT_SEMANTIC_REGISTER = ROOT / "docs" / "specs" / "WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md"
DEFAULT_OUTPUT = ROOT / "artifacts" / "wave1_phase_b2_ask_first_boundary_diagnostic.json"

CASE_ID = "B2-004"
INPUT_MESSAGE = "我吃了滷味"
SEMANTIC_DECISION_ID = "self_selected_basket_without_listed_items"

ROOT_CAUSES = (
    "phase_a_gap",
    "b1_b2_boundary_gap",
    "evidence_source_selection_gap",
    "evidence_packet_gate_gap",
    "live_payload_gap",
    "validator_classification_gap",
    "none",
)


def diagnose_b1_b2_ask_first_boundary(
    *,
    phase_b2_report: dict[str, Any],
    phase_b_report: dict[str, Any] | None = None,
    live_report: dict[str, Any] | None = None,
    semantic_register_text: str = "",
) -> dict[str, Any]:
    b1 = _diagnose_phase_a_b1(phase_b_report)
    b2_case = _case_by_id(phase_b2_report, CASE_ID)
    source_selection = _diagnose_evidence_source_selection(b2_case)
    boundary = _diagnose_b1_b2_boundary(b2_case)
    packet_gate = _diagnose_evidence_packet_gate(b2_case)
    semantic_policy = _semantic_policy(semantic_register_text)
    live_payload = _diagnose_live_payload(b2_case)
    validator = _diagnose_validator(live_report, semantic_policy)

    primary = _primary_root_cause(
        b1=b1,
        boundary=boundary,
        source_selection=source_selection,
        packet_gate=packet_gate,
        live_payload=live_payload,
        validator=validator,
        semantic_policy=semantic_policy,
    )
    contributing = _contributing_factors(semantic_policy=semantic_policy, primary=primary, validator=validator)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "diagnostic": "b1_b2_ask_first_boundary",
        "case_id": CASE_ID,
        "input": INPUT_MESSAGE,
        "primary_root_cause": primary,
        "contributing_factors": contributing,
        "semantic_policy": semantic_policy,
        "phase_a_b1": b1,
        "b1_b2_boundary": boundary,
        "evidence_source_selection": source_selection,
        "evidence_packet_gate": packet_gate,
        "live_payload": live_payload,
        "validator": validator,
        "fixes_attempted": False,
        "canonical_truth_changed": False,
    }


def _diagnose_phase_a_b1(phase_b_report: dict[str, Any] | None) -> dict[str, Any]:
    if not phase_b_report:
        return {"status": "not_observed", "reason": "phase_b_report_not_provided"}
    trace = _b1_trace(phase_b_report)
    if not trace:
        return {"status": "not_observed", "reason": "b1_004_trace_not_found"}
    manager_pass_1 = _dict(trace.get("manager_pass_1"))
    decision_payload = _dict(manager_pass_1.get("decision_payload"))
    router = _dict(trace.get("runtime_tool_router"))
    mutation = _dict(trace.get("mutation"))
    requested_read_tools = _strings(manager_pass_1.get("requested_read_tools") or router.get("requested_read_tools"))
    allowed_tools = _strings(router.get("allowed_tools"))
    blocked_tools = _strings(router.get("blocked_tools"))
    mutation_attempted = mutation.get("mutation_attempted") is True
    bad_final_action = str(decision_payload.get("final_action") or "") in {
        "log_food",
        "log_consumption",
        "record_food",
        "commit",
    }
    lookup_or_search_requested = any(tool in {"lookup_generic_food", "retrieve_web_food_evidence", "search"} for tool in requested_read_tools)
    lookup_or_search_allowed = any(tool in {"lookup_generic_food", "retrieve_web_food_evidence", "search"} for tool in allowed_tools)
    gap = mutation_attempted or bad_final_action or lookup_or_search_allowed or lookup_or_search_requested
    return {
        "status": "gap" if gap else "pass",
        "intent": "food_logging",
        "clarify_posture": "request_clarification" if not gap else "not_proven",
        "semantic_boundary": trace.get("semantic_boundary"),
        "requested_read_tools": requested_read_tools,
        "allowed_tools": allowed_tools,
        "blocked_tools": blocked_tools,
        "mutation_allowed": not mutation_attempted,
        "mutation_attempted": mutation_attempted,
        "pass2_ran": bool(_list(_dict(trace.get("manager_pass_2")).get("item_results"))),
        "decision_payload": decision_payload,
    }


def _diagnose_b1_b2_boundary(b2_case: dict[str, Any]) -> dict[str, Any]:
    source_selection = _dict(b2_case.get("source_selection"))
    producer_trace = _dict(b2_case.get("producer_trace"))
    packets = [_dict(packet) for packet in _list(b2_case.get("packets"))]
    semantic_packet_present = any(packet.get("semantic_problem") == "composition_unknown" for packet in packets)
    clarify_support_observed = (
        source_selection.get("evidence_required") == "clarify_support"
        or producer_trace.get("support_basis") == "clarify_support"
        or semantic_packet_present
    )
    return {
        "status": "pass" if clarify_support_observed else "gap",
        "clarify_support_observed": clarify_support_observed,
        "producer_support_basis": producer_trace.get("support_basis"),
        "semantic_packet_present": semantic_packet_present,
        "semantic_problem": "composition_unknown" if semantic_packet_present else None,
    }


def _diagnose_evidence_source_selection(b2_case: dict[str, Any]) -> dict[str, Any]:
    source_selection = _dict(b2_case.get("source_selection"))
    expected = source_selection.get("source_path") == "ask_user" and source_selection.get("evidence_required") == "clarify_support"
    return {
        "status": "pass" if expected else "gap",
        "source_path": source_selection.get("source_path"),
        "evidence_required": source_selection.get("evidence_required"),
        "product_policy_status": source_selection.get("product_policy_status"),
        "web_allowed": source_selection.get("web_allowed"),
        "decides_logged_or_draft": source_selection.get("decides_logged_or_draft"),
        "expected_source_path": "ask_user",
        "expected_evidence_required": "clarify_support",
    }


def _diagnose_evidence_packet_gate(b2_case: dict[str, Any]) -> dict[str, Any]:
    item_results = [_dict(item) for item in _list(_dict(b2_case.get("manager_pass_2")).get("item_results"))]
    packets = [_dict(packet) for packet in _list(b2_case.get("packets"))]
    has_estimate = any(_has_estimate(item) for item in item_results)
    has_evidence = any(bool(_list(item.get("evidence_used"))) for item in item_results)
    mutation_attempted = _dict(b2_case.get("mutation")).get("mutation_attempted") is True
    semantic_rule_hint = any(packet.get("rule_id") == "self_selected_basket_without_ingredients" for packet in packets)
    gap = has_estimate or has_evidence or mutation_attempted
    return {
        "status": "gap" if gap else "pass",
        "ask_first_required": semantic_rule_hint,
        "synthesis_allowed": not semantic_rule_hint,
        "item_results_allowed": not semantic_rule_hint,
        "estimate_allowed": False if semantic_rule_hint else True,
        "has_estimate": has_estimate,
        "has_evidence_refs": has_evidence,
        "mutation_attempted": mutation_attempted,
        "item_result_count": len(item_results),
        "item_results_exactness": [item.get("exactness_posture") for item in item_results],
    }


def _diagnose_live_payload(b2_case: dict[str, Any]) -> dict[str, Any]:
    payload = build_provider_request_payload_for_case(b2_case)
    source_selection = _dict(b2_case.get("source_selection"))
    ask_first = source_selection.get("source_path") == "ask_user"
    required_output = _dict(payload.get("required_output"))
    clarify_only_contract = payload.get("contract_type") == "clarify_only"
    item_results_allowed = payload.get("item_results_allowed") is True
    estimate_allowed = payload.get("estimate_allowed") is True
    gap = ask_first and (not clarify_only_contract or item_results_allowed or estimate_allowed)
    return {
        "status": "gap" if gap else "pass",
        "task_type": "ordinary_packet_synthesis" if gap else str(payload.get("contract_type") or "unknown"),
        "item_results_required": required_output.get("top_level_key") == "item_results",
        "item_results_allowed": item_results_allowed,
        "estimate_allowed": estimate_allowed,
        "kcal_range_allowed": payload.get("kcal_range_allowed") is True,
        "clarify_only_contract_present": clarify_only_contract,
        "expected_output": payload.get("expected_output") or required_output.get("expected_output"),
        "reason": "ask_first_case_was_sent_with_generic_item_results_contract" if gap else "clarify_only_contract_observed",
    }


def _diagnose_validator(live_report: dict[str, Any] | None, semantic_policy: dict[str, Any]) -> dict[str, Any]:
    case_result = _live_case(live_report)
    actual = case_result.get("verdict_category") if case_result else None
    model_estimated = "unknown_composition_estimated" in _strings(case_result.get("product_decisions_required") if case_result else [])
    ask_first_blocker = case_result and case_result.get("failure_family") == "b2_ask_first_policy_violation"
    expected = "readiness_blocker" if semantic_policy["status"] == "approved" and (model_estimated or ask_first_blocker) else actual
    status = "gap" if expected and actual != expected else "pass"
    return {
        "status": status,
        "actual_verdict": actual,
        "expected_verdict": expected,
        "model_estimated_unknown_composition": model_estimated,
        "ask_first_policy_violation": bool(ask_first_blocker),
        "mismatch": actual != expected if expected else False,
    }


def _semantic_policy(register_text: str) -> dict[str, Any]:
    match = re.search(
        rf"(?ms)^\s*{re.escape(SEMANTIC_DECISION_ID)}:\s*\n(?P<body>(?:^\s{{4,}}.*\n?)*)",
        register_text,
    )
    if match is None:
        return {"decision_id": SEMANTIC_DECISION_ID, "status": "missing", "selected_policy": None}
    section = match.group("body")
    status = _yaml_value_after(section, "status") or "pending"
    selected_policy = _yaml_value_after(section, "selected_policy")
    return {"decision_id": SEMANTIC_DECISION_ID, "status": status, "selected_policy": selected_policy}


def _primary_root_cause(
    *,
    b1: dict[str, Any],
    boundary: dict[str, Any],
    source_selection: dict[str, Any],
    packet_gate: dict[str, Any],
    live_payload: dict[str, Any],
    validator: dict[str, Any],
    semantic_policy: dict[str, Any],
) -> str:
    if semantic_policy.get("status") == "approved" and validator.get("status") == "gap":
        return "validator_classification_gap"
    checks = (
        ("phase_a_gap", b1),
        ("b1_b2_boundary_gap", boundary),
        ("evidence_source_selection_gap", source_selection),
        ("evidence_packet_gate_gap", packet_gate),
        ("live_payload_gap", live_payload),
        ("validator_classification_gap", validator),
    )
    for root_cause, payload in checks:
        if payload.get("status") == "gap":
            return root_cause
    return "none"


def _contributing_factors(*, semantic_policy: dict[str, Any], primary: str, validator: dict[str, Any]) -> list[str]:
    factors: list[str] = []
    if semantic_policy["status"] == "missing":
        factors.append("semantic_register_policy_missing")
    elif semantic_policy["status"] == "pending":
        factors.append("semantic_register_policy_pending")
    if validator.get("model_estimated_unknown_composition") is True and primary != "validator_classification_gap":
        factors.append("live_model_estimated_unknown_composition")
    return factors


def _b1_trace(phase_b_report: dict[str, Any]) -> dict[str, Any] | None:
    for trace in _list(phase_b_report.get("tool_loop_traces")):
        trace_dict = _dict(trace)
        if trace_dict.get("case_id") == "B1-004" or trace_dict.get("input_message") == INPUT_MESSAGE:
            return trace_dict
    return None


def _case_by_id(report: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in _list(report.get("cases")):
        case_dict = _dict(case)
        if case_dict.get("case_id") == case_id:
            return case_dict
    raise KeyError(f"Missing case_id={case_id}")


def _live_case(live_report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not live_report:
        return None
    for case in _list(live_report.get("case_results")):
        case_dict = _dict(case)
        if case_dict.get("case_id") == CASE_ID:
            return case_dict
    return None


def _has_estimate(item: dict[str, Any]) -> bool:
    if item.get("likely_kcal") is not None:
        return True
    kcal_range = item.get("kcal_range")
    return isinstance(kcal_range, list) and any(value is not None for value in kcal_range)


def _yaml_value_after(text: str, key: str) -> str | None:
    marker = f"{key}:"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(marker):
            continue
        value = stripped[len(marker) :].strip()
        return value or None
    return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in _list(value)]


def _read_json_optional(path_text: str | None) -> dict[str, Any] | None:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_text_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose B-1/B2 ask-first boundary for B2-004.")
    parser.add_argument("--phase-b-report", default=None)
    parser.add_argument("--phase-b2-report", default=str(DEFAULT_PHASE_B2_REPORT))
    parser.add_argument("--live-report", default=str(DEFAULT_LIVE_REPORT))
    parser.add_argument("--semantic-register", default=str(DEFAULT_SEMANTIC_REGISTER))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    phase_b2_report = _read_json_optional(args.phase_b2_report)
    if phase_b2_report is None:
        raise SystemExit(f"Missing phase B2 report: {args.phase_b2_report}")
    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_read_json_optional(args.phase_b_report),
        phase_b2_report=phase_b2_report,
        live_report=_read_json_optional(args.live_report),
        semantic_register_text=_read_text_optional(Path(args.semantic_register)),
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": output_path.as_posix(),
                "primary_root_cause": report["primary_root_cause"],
                "contributing_factors": report["contributing_factors"],
                "semantic_policy": report["semantic_policy"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


__all__ = ["diagnose_b1_b2_ask_first_boundary"]


if __name__ == "__main__":
    raise SystemExit(main())
