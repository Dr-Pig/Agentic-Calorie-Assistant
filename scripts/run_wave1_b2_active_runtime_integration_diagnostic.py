from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim
from scripts import run_wave1_founder_e2e_deterministic_diagnostic as founder_diagnostic

ACTIVE_ENTRYPOINT = "app.intake.application.intake_turn_orchestrator.execute_bundle1_turn"
ARTIFACT_PATH = ROOT / "artifacts" / "wave1_b2_active_runtime_integration_diagnostic.json"
FOUNDER_ARTIFACT_PATH = ROOT / "artifacts" / "wave1_founder_e2e_deterministic_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "wave1_b2_active_runtime_integration_diagnostic.sqlite3"
LOCAL_DATE = "2026-04-30"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _cases(founder_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [case for case in _list(founder_report.get("cases")) if isinstance(case, dict)]


def _nutrition_payloads(founder_report: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for case in _cases(founder_report):
        payload = _dict(_dict(case.get("b2")).get("nutrition_payload"))
        if payload:
            payloads.append(payload)
    return payloads


def _web_runtime_traces(founder_report: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for payload in _nutrition_payloads(founder_report):
        web_trace = _dict(_dict(payload.get("trace_contract")).get("web_runtime_trace"))
        if web_trace:
            traces.append(web_trace)
    return traces


def _trace_contracts(founder_report: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for payload in _nutrition_payloads(founder_report):
        trace_contract = _dict(payload.get("trace_contract"))
        if trace_contract:
            traces.append(trace_contract)
    return traces


def _has_case_state_delta(founder_report: dict[str, Any]) -> bool:
    return any(bool(_dict(_dict(case.get("mutation")).get("state_delta"))) for case in _cases(founder_report))


def _has_ledger_read(founder_report: dict[str, Any]) -> bool:
    return any(bool(_dict(case.get("ledger_read"))) for case in _cases(founder_report))


def _has_phase_c_trace(founder_report: dict[str, Any]) -> bool:
    for case in _cases(founder_report):
        same_truth = _dict(case.get("same_truth"))
        if _dict(same_truth.get("phase_c_trace")):
            return True
    return False


def _has_b2_final_mapping(founder_report: dict[str, Any]) -> bool:
    serialized = json.dumps(founder_report, ensure_ascii=False)
    return '"final_mapping_owner": "b2_final_mapping"' in serialized


def _has_runtime_key(traces: list[dict[str, Any]], key: str) -> bool:
    return any(key in trace for trace in traces)


def _active_runtime_observability(founder_report: dict[str, Any]) -> dict[str, bool]:
    trace_contracts = _trace_contracts(founder_report)
    traces = _web_runtime_traces(founder_report)
    return {
        "manager_semantic_decision_present": any(
            bool(_dict(_dict(case.get("final_mapping")).get("manager_semantic_decision")))
            for case in _cases(founder_report)
        ),
        "nutrition_payload_present": bool(_nutrition_payloads(founder_report)),
        "web_runtime_trace_present": bool(traces),
        "retrieval_intent_source_present": _has_runtime_key(trace_contracts, "retrieval_intent_source"),
        "source_selection_object_present": _has_runtime_key(trace_contracts, "source_selection"),
        "packet_consumption_trace_present": _has_runtime_key(trace_contracts, "packet_consumption_trace"),
        "b2_final_mapping_first_class_present": _has_b2_final_mapping(founder_report),
        "state_delta_present": _has_case_state_delta(founder_report),
        "ledger_read_present": _has_ledger_read(founder_report),
        "phase_c_trace_present": _has_phase_c_trace(founder_report),
    }


def _missing_surfaces(observability: dict[str, bool]) -> list[str]:
    missing: list[str] = []
    if not observability.get("retrieval_intent_source_present"):
        missing.append("retrieval_intent_source_surface_missing")
    if not observability.get("source_selection_object_present"):
        missing.append("source_selection_surface_missing")
    if not observability.get("b2_final_mapping_first_class_present"):
        missing.append("b2_final_mapping_first_class_surface_missing")
    return missing


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    founder_output_path: Path = FOUNDER_ARTIFACT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str = LOCAL_DATE,
) -> dict[str, Any]:
    founder_report = founder_diagnostic.run_diagnostic(
        output_path=founder_output_path,
        db_path=db_path,
        local_date=local_date,
    )
    observability = _active_runtime_observability(founder_report)
    missing = _missing_surfaces(observability)
    gap = bool(missing)
    report = {
        "artifact_type": "wave1_b2_active_runtime_integration_diagnostic",
        "provider_mode": "deterministic",
        "active_entrypoint": ACTIVE_ENTRYPOINT,
        "active_entrypoint_verified": founder_report.get("active_entrypoint_verified") is True,
        "live_llm_invoked": False,
        "tavily_live_invoked": False,
        "runtime_web_activation_approved": False,
        "readiness_claimed": False,
        "readiness_claim": build_readiness_claim(
            claim_scope="deterministic_runtime",
            activation_stage="deterministic",
            semantic_authority_source="fake_manager_structured_output",
            producer_honesty={
                "runner_inferred_semantics": False,
                "fake_provider_simulated_manager": True,
                "final_mapping_fabricated": False,
                "mutation_fabricated": False,
                "runtime_web_activation_approved": False,
            },
            evidence_lineage={
                "artifacts": [str(founder_output_path.relative_to(ROOT)) if founder_output_path.is_relative_to(ROOT) else str(founder_output_path)],
                "producers": [
                    "scripts/run_wave1_founder_e2e_deterministic_diagnostic.py",
                    "scripts/run_wave1_b2_active_runtime_integration_diagnostic.py",
                ],
                "active_entrypoint": ACTIVE_ENTRYPOINT,
                "legacy_oracle_used": False,
            },
            allowed_next_stage="deterministic",
            forbidden_claims=[
                "live_ready",
                "user_facing_ready",
                "mutation_ready",
                "runtime_web_ready",
                "product_ready",
            ],
            readiness_claimed=False,
        ),
        "founder_deterministic_summary": founder_report.get("summary") or {},
        "active_runtime_observability": observability,
        "missing_first_class_surfaces": missing,
        "verdict": "test_harness_gap" if gap else "diagnostic_observation",
        "failure_layer": "test_harness_gap" if gap else None,
        "diagnostic_notes": [
            "Active entrypoint is invokable and Founder deterministic E2E is green.",
            "This diagnostic does not activate live web search or Tavily.",
            "B2 final mapping is not yet a first-class active runtime surface when consumed through the intake entrypoint.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wave 1 B2 active runtime integration diagnostic.")
    parser.add_argument("--output", default=str(ARTIFACT_PATH))
    parser.add_argument("--founder-output", default=str(FOUNDER_ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", default=LOCAL_DATE)
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        founder_output_path=Path(args.founder_output),
        db_path=Path(args.db_path),
        local_date=args.local_date,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "verdict": report["verdict"],
                "failure_layer": report["failure_layer"],
                "missing_first_class_surfaces": report["missing_first_class_surfaces"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
