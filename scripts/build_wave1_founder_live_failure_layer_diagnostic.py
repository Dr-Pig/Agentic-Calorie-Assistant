from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim


DEFAULT_FOUNDER_LIVE_ARTIFACT = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_bundle1_turn"


def build_founder_live_failure_layer_diagnostic(founder_live_artifact: dict[str, Any]) -> dict[str, Any]:
    cases = [_case_trace(case) for case in _focus_cases(founder_live_artifact)]
    return _json_safe(
        {
            "artifact_type": "wave1_founder_live_failure_layer_diagnostic",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": founder_live_artifact.get("artifact_type"),
            "source_artifact": str(founder_live_artifact.get("source_artifact") or DEFAULT_FOUNDER_LIVE_ARTIFACT),
            "current_mainline": "Wave 1 Founder live failure-layer closure",
            "provider_mode": founder_live_artifact.get("provider_mode"),
            "live_invoked": founder_live_artifact.get("live_invoked") is True,
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(),
            "production_selected": False,
            "runtime_web_activation_approved": False,
            "mutation_enabled": False,
            "active_entrypoint": founder_live_artifact.get("active_entrypoint") or ACTIVE_ENTRYPOINT,
            "input_integrity": _input_integrity(founder_live_artifact),
            "summary": _summary(cases),
            "focus_cases": cases,
        }
    )


def write_founder_live_failure_layer_diagnostic(
    *,
    founder_live_artifact_path: Path = DEFAULT_FOUNDER_LIVE_ARTIFACT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    founder_live_artifact = json.loads(founder_live_artifact_path.read_text(encoding="utf-8"))
    founder_live_artifact["source_artifact"] = str(founder_live_artifact_path)
    report = build_founder_live_failure_layer_diagnostic(founder_live_artifact)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "wave1_founder_live_failure_layer_diagnostic.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _focus_cases(founder_live_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        case
        for case in _list(founder_live_artifact.get("cases"))
        if isinstance(case, dict) and str(case.get("verdict") or "") != "pass"
    ]


def _case_trace(case: dict[str, Any]) -> dict[str, Any]:
    actual = _dict(case.get("actual_behavior"))
    phase_a = _dict(case.get("phase_a"))
    b2 = _dict(case.get("b2"))
    final_mapping = _dict(case.get("final_mapping"))
    mutation = _dict(case.get("mutation"))
    state_delta = _dict(mutation.get("state_delta"))
    nutrition_payload = _dict(b2.get("nutrition_payload"))
    trace_contract = _dict(nutrition_payload.get("trace_contract"))
    item_final_mapping = _first_b2_final_mapping(b2)

    tool_trace = _tool_trace(b2, actual=actual)
    b2_trace = {
        "nutrition_payload_present": bool(nutrition_payload),
        "estimated_kcal": _estimated_kcal(nutrition_payload),
        "retrieval_intent_source": trace_contract.get("retrieval_intent_source", "not_available"),
        "source_selection": trace_contract.get("source_selection", "not_available"),
        "packet_consumption_trace": trace_contract.get("packet_consumption_trace", "not_available"),
        "web_runtime_trace_present": bool(_dict(trace_contract.get("web_runtime_trace"))),
    }
    final_mapping_trace = {
        "observable": final_mapping.get("observable") is True,
        "manager_final_action": final_mapping.get("manager_final_action"),
        "b2_final_mapping_present": bool(item_final_mapping),
        "external_outcome": item_final_mapping.get("external_outcome", "not_available"),
        "final_mapping_owner": item_final_mapping.get("final_mapping_owner", "not_available"),
        "persistence_result_observable": final_mapping.get("persistence_result_observable") is True,
    }
    persistence_trace = {
        "persistence_result_present": bool(_dict(mutation.get("persistence_result"))),
        "persistence_result": _dict(mutation.get("persistence_result")) or "not_available",
    }
    state_delta_trace = {
        "state_delta_present": bool(state_delta),
        "state_delta": state_delta,
        "canonical_commit_status": state_delta.get("canonical_commit", "not_available"),
    }
    failure_sublayers = _failure_sublayers(
        case=case,
        tool_trace=tool_trace,
        b2_trace=b2_trace,
        final_mapping_trace=final_mapping_trace,
        persistence_trace=persistence_trace,
    )
    return {
        "case_id": case.get("case_id"),
        "verdict": case.get("verdict"),
        "observed_failure_layer": case.get("failure_layer"),
        "observed_failure_family": case.get("failure_family"),
        "case_contract_status": case.get("case_contract_status"),
        "failure_sublayers": failure_sublayers,
        "manager_trace": {
            "manager_intent": actual.get("manager_intent"),
            "manager_final_action": actual.get("manager_final_action"),
            "semantic_decision_present": bool(_dict(actual.get("manager_semantic_decision"))),
            "semantic_decision": _dict(actual.get("manager_semantic_decision")),
        },
        "tool_trace": tool_trace,
        "b2_trace": b2_trace,
        "final_mapping_trace": final_mapping_trace,
        "transition_guard_trace": _surface_trace(_dict(phase_a.get("transition_guard_result"))),
        "commit_boundary_trace": _surface_trace(_dict(phase_a.get("phase_a_commit_boundary_preflight"))),
        "persistence_trace": persistence_trace,
        "state_delta_trace": state_delta_trace,
        "same_truth_trace": {
            "phase_c_trace_present": bool(_dict(_dict(case.get("same_truth")).get("phase_c_trace"))),
            "same_truth_closure_gate_present": bool(_dict(_dict(case.get("same_truth")).get("same_truth_closure_gate"))),
        },
        "fabrication_guard": {
            "runner_inferred_semantics": False,
            "nutrition_payload_fabricated": False,
            "final_mapping_fabricated": False,
            "canonical_commit_fabricated": False,
        },
    }


def _tool_trace(b2: dict[str, Any], *, actual: dict[str, Any]) -> dict[str, Any]:
    tool_results = [item for item in _list(b2.get("tool_results")) if isinstance(item, dict)]
    manager_tool_calls = _manager_tool_calls(actual)
    return {
        "tool_results_observable": bool(tool_results),
        "tool_results_count": len(tool_results),
        "tool_names": [str(item.get("tool_name") or item.get("name") or "unknown") for item in tool_results],
        "tool_calls_observable": manager_tool_calls != "not_available",
        "manager_tool_calls": manager_tool_calls,
    }


def _manager_tool_calls(actual: dict[str, Any]) -> list[dict[str, Any]] | str:
    calls: list[dict[str, Any]] = []
    for round_item in _list(actual.get("manager_rounds")):
        decision = _dict(_dict(round_item).get("decision"))
        for call in _list(decision.get("tool_calls")):
            if isinstance(call, dict):
                calls.append(dict(call))
    return calls if calls else "not_available"


def _failure_sublayers(
    *,
    case: dict[str, Any],
    tool_trace: dict[str, Any],
    b2_trace: dict[str, Any],
    final_mapping_trace: dict[str, Any],
    persistence_trace: dict[str, Any],
) -> list[str]:
    sublayers: list[str] = []
    failure_layer = str(case.get("failure_layer") or "")
    if tool_trace.get("manager_tool_calls") == "not_available" and tool_trace.get("tool_results_count") == 0:
        sublayers.append("manager_skipped_tool_path")
    if b2_trace.get("nutrition_payload_present") is False:
        sublayers.append("payload_absent_before_b2")
    if final_mapping_trace.get("b2_final_mapping_present") is False:
        sublayers.append("b2_final_mapping_absent")
    if persistence_trace.get("persistence_result_present") is False and failure_layer in {"b2", "mutation"}:
        sublayers.append("persistence_not_attempted")
    if failure_layer == "deferred_source_limitation" and b2_trace.get("web_runtime_trace_present") is False:
        sublayers.append("deferred_source_unobservable_no_b2_trace")
    return sublayers


def _estimated_kcal(nutrition_payload: dict[str, Any]) -> int | str:
    if not nutrition_payload:
        return "not_available"
    for key in ("estimated_kcal", "likely_kcal", "kcal"):
        value = nutrition_payload.get(key)
        if isinstance(value, int):
            return value
    return "not_available"


def _first_b2_final_mapping(b2: dict[str, Any]) -> dict[str, Any]:
    payload = _dict(b2.get("nutrition_payload"))
    trace_contract = _dict(payload.get("trace_contract"))
    for key in ("b2_final_mapping", "final_mapping"):
        mapping = _dict(trace_contract.get(key))
        if mapping.get("final_mapping_owner") == "b2_final_mapping":
            return mapping
    item_results = _list(trace_contract.get("item_results"))
    for item in item_results:
        mapping = _dict(_dict(item).get("final_mapping"))
        if mapping.get("final_mapping_owner") == "b2_final_mapping":
            return mapping
    return {}


def _surface_trace(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "present": bool(surface),
        "payload": surface or "not_available",
    }


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    layers = sorted({str(case.get("observed_failure_layer")) for case in cases if case.get("observed_failure_layer")})
    sublayer_counts: dict[str, int] = {}
    for case in cases:
        for sublayer in _list(case.get("failure_sublayers")):
            key = str(sublayer)
            sublayer_counts[key] = sublayer_counts.get(key, 0) + 1
    return {
        "focus_case_count": len(cases),
        "failure_layers": layers,
        "failure_sublayers": dict(sorted(sublayer_counts.items())),
        "b2_failure_count": sum(1 for case in cases if case.get("observed_failure_layer") == "b2"),
        "mutation_failure_count": sum(1 for case in cases if case.get("observed_failure_layer") == "mutation"),
        "deferred_source_limitation_count": sum(
            1 for case in cases if case.get("observed_failure_layer") == "deferred_source_limitation"
        ),
        "provider_contract_failure_count": sum(
            1 for case in cases if case.get("observed_failure_layer") == "provider_contract_non_adherence"
        ),
    }


def _input_integrity(founder_live_artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if founder_live_artifact.get("artifact_type") != "wave1_founder_e2e_live_diagnostic":
        blockers.append("input_artifact_type_invalid")
    if founder_live_artifact.get("readiness_claimed") is True:
        blockers.append("input_readiness_claimed")
    if founder_live_artifact.get("production_selected") is True:
        blockers.append("input_production_selected")
    if founder_live_artifact.get("runtime_web_activation_approved") is True:
        blockers.append("input_runtime_web_activation_approved")
    if founder_live_artifact.get("mutation_enabled") is True:
        blockers.append("input_mutation_enabled")
    return {
        "passed": not blockers,
        "blockers": sorted(set(blockers)),
    }


def _readiness_claim() -> dict[str, Any]:
    return build_readiness_claim(
        claim_scope="live_diagnostic",
        activation_stage="live_diagnostic",
        semantic_authority_source="deterministic_validator",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": False,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": ["artifacts/wave1_founder_e2e_live_diagnostic.json"],
            "producers": ["scripts/build_wave1_founder_live_failure_layer_diagnostic.py"],
            "active_entrypoint": ACTIVE_ENTRYPOINT,
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=[
            "product_ready",
            "user_facing_ready",
            "mutation_ready",
            "production_ready",
            "runtime_web_activation_ready",
        ],
        readiness_claimed=False,
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Wave 1 Founder live failure-layer diagnostic.")
    parser.add_argument("--founder-live-artifact", default=str(DEFAULT_FOUNDER_LIVE_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    output_path = write_founder_live_failure_layer_diagnostic(
        founder_live_artifact_path=Path(args.founder_live_artifact),
        output_dir=Path(args.output_dir),
    )
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
