from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_GATE_LEDGER_PATH = ROOT / "docs" / "quality" / "MANAGER_RUNTIME_GATE_LEDGER.yaml"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14h_limited_live_ladder_closeout.json"
TARGET_GATE_ID = "rt14_limited_live_ladder"
REQUIRED_CLOSEOUT_ARTIFACT_GATES = (
    "rt9b_fooddb_packet_live_probe",
    "rt9c_websearch_candidate_live_probe",
    "rt10c_exact_item_live_quality_probe",
    "rt10d_generic_optional_refinement_live_probe",
    "rt10e_blocking_clarify_correction_live_probe",
    "rt11b_final_response_quality_live_wall",
    "rt11c_renderer_input_basis_evidence_pack",
    "rt12b_live_trace_grading_extension",
    "rt13b_latency_cost_cache_budget_pack",
    "rt14f_holdout_replay_anti_overfit_gate",
    "rt14g_response_language_prompt_polish",
)
CONTRACT_ONLY_ARTIFACT_GATES = {"rt14g_response_language_prompt_polish"}
ALLOWED_CLOSEOUT_DECISION_OPTIONS = {
    "offline_shadow_replay",
    "prepare_private_self_use_candidate",
}
FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "whole_product_mvp_ready",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
    "fooddb_truth_updated",
)


def build_rt14h_limited_live_ladder_closeout(
    *,
    gate_ledger: dict[str, Any],
    gate_artifacts: dict[str, dict[str, Any]],
    live_decision_pack: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    gates = {
        str(gate.get("gate_id") or ""): gate
        for gate in _list(gate_ledger.get("gates"))
        if isinstance(gate, dict)
    }
    ladder_gate = gates.get(TARGET_GATE_ID, {})
    dependencies = [str(item) for item in _list(ladder_gate.get("depends_on"))]
    cases = [
        _ledger_case(gate_ledger, gates, ladder_gate, dependencies),
        _gate_artifacts_case(gate_artifacts),
        _decision_pack_case(live_decision_pack),
        _claim_boundary_case([*gate_artifacts.values(), live_decision_pack]),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_name": resolved_output_path.name,
            "artifact_path": str(resolved_output_path),
            "artifact_type": "accurate_intake_rt14h_limited_live_ladder_closeout",
            "claim_scope": "manager_runtime_limited_live_ladder_closeout",
            "launch_scope": "current_shell_v1",
            "producer_track": "CurrentShell/ManagerRuntime",
            "target_manager_runtime_gate": TARGET_GATE_ID,
            "pass_type": "runtime_backed",
            "runtime_backed": True,
            "live_llm_invoked": True,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "status": _status(blockers),
            "blockers": blockers,
            "summary": {
                "dependency_gate_count": len(dependencies),
                "green_dependency_gate_count": sum(
                    1 for gate_id in dependencies if _gate_status(gates.get(gate_id)) == "green"
                ),
                "artifact_gate_count": len(gate_artifacts),
                "required_artifact_gate_count": len(REQUIRED_CLOSEOUT_ARTIFACT_GATES),
                "runtime_backed_artifact_count": sum(
                    1 for artifact in gate_artifacts.values() if artifact.get("runtime_backed") is True
                ),
                "live_artifact_count": sum(
                    1 for artifact in gate_artifacts.values() if artifact.get("live_llm_invoked") is True
                ),
            },
            "decision_pack_sync": _decision_pack_sync(live_decision_pack),
            "semantic_boundary": {
                "deterministic_role": "validate_gate_closure_and_claim_boundary",
                "llm_role": "already_exercised_by_upstream_live_gates",
                "deterministic_must_not_select_intent": True,
                "deterministic_must_not_rewrite_manager_semantics": True,
            },
            "cases": cases,
            "non_claims": {
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "whole_product_mvp_ready": False,
                "production_selected": False,
                "mutation_rollout_approved": False,
            },
        }
    )


def _ledger_case(
    gate_ledger: dict[str, Any],
    gates: dict[str, dict[str, Any]],
    ladder_gate: dict[str, Any],
    dependencies: list[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    if gate_ledger.get("artifact_type") != "manager_runtime_gate_ledger":
        blockers.append("unexpected_ledger_artifact_type")
    if gate_ledger.get("launch_scope") != "current_shell_v1":
        blockers.append("unexpected_launch_scope")
    if gate_ledger.get("owner") != "ManagerRuntime":
        blockers.append("owner_not_manager_runtime")
    if not ladder_gate:
        blockers.append(f"missing_gate:{TARGET_GATE_ID}")
    if _gate_status(ladder_gate) not in {"pending", "green"}:
        blockers.append(f"{TARGET_GATE_ID}_unexpected_status:{_gate_status(ladder_gate)}")
    for gate_id in dependencies:
        if gate_id not in gates:
            blockers.append(f"{gate_id}_missing")
        elif _gate_status(gates[gate_id]) != "green":
            blockers.append(f"{gate_id}_not_green")
    return _case(
        "ledger_dependency",
        blockers,
        {
            "target_gate_status": _gate_status(ladder_gate),
            "dependency_gate_count": len(dependencies),
        },
    )


def _gate_artifacts_case(gate_artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    observed: dict[str, Any] = {}
    for gate_id in REQUIRED_CLOSEOUT_ARTIFACT_GATES:
        artifact = gate_artifacts.get(gate_id)
        if not isinstance(artifact, dict):
            blockers.append(f"{gate_id}_missing")
            continue
        observed[gate_id] = {
            "target_manager_runtime_gate": artifact.get("target_manager_runtime_gate"),
            "status": artifact.get("status"),
            "runtime_backed": artifact.get("runtime_backed"),
            "live_llm_invoked": artifact.get("live_llm_invoked"),
        }
        if artifact.get("target_manager_runtime_gate") != gate_id:
            blockers.append(f"{gate_id}_unexpected_gate")
        if artifact.get("status") != "pass":
            blockers.append(f"{gate_id}_not_pass")
        if gate_id not in CONTRACT_ONLY_ARTIFACT_GATES:
            if artifact.get("runtime_backed") is not True:
                blockers.append(f"{gate_id}_not_runtime_backed")
            if artifact.get("live_llm_invoked") is not True:
                blockers.append(f"{gate_id}_live_llm_not_invoked")
    return _case("gate_artifact", blockers, observed)


def _decision_pack_case(live_decision_pack: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if live_decision_pack.get("artifact_type") != "accurate_intake_mvp_live_decision_pack":
        blockers.append("unexpected_artifact_type")
    selected_option = str(live_decision_pack.get("selected_option") or "")
    if selected_option not in ALLOWED_CLOSEOUT_DECISION_OPTIONS:
        blockers.append(f"blocking_selected_option:{selected_option}")
    decision_boundary = _dict(live_decision_pack.get("decision_boundary"))
    for flag in (
        "live_diagnostic_is_product_readiness",
        "runtime_web_activation_allowed",
        "mutation_rollout_allowed",
        "production_manager_selected",
    ):
        if decision_boundary.get(flag) is True:
            blockers.append(f"decision_boundary_{flag}")
    return _case("decision_pack", blockers, _decision_pack_sync(live_decision_pack))


def _claim_boundary_case(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    for index, artifact in enumerate(artifacts):
        non_claims = _dict(artifact.get("non_claims"))
        for flag in FORBIDDEN_TRUE_FLAGS:
            if _truthy(artifact.get(flag)) or _truthy(non_claims.get(flag)):
                blockers.append(f"source_{index}_{flag}")
    return _case(
        "claim_boundary",
        blockers,
        {"forbidden_true_flags_checked": list(FORBIDDEN_TRUE_FLAGS)},
    )


def _decision_pack_sync(live_decision_pack: dict[str, Any]) -> dict[str, Any]:
    selected_option = str(live_decision_pack.get("selected_option") or "")
    return {
        "source_artifact_type": live_decision_pack.get("artifact_type"),
        "selected_option": selected_option,
        "selection_reason": live_decision_pack.get("selection_reason"),
        "private_self_use_candidate_prepared": (
            live_decision_pack.get("private_self_use_candidate_prepared") is True
        ),
        "next_mainline": _next_mainline(selected_option),
    }


def _next_mainline(selected_option: str) -> str:
    if selected_option == "prepare_private_self_use_candidate":
        return "handoff_to_shared_dogfood_candidate_pack"
    if selected_option == "offline_shadow_replay":
        return "continue_current_shell_appshell_browser_runtime_closure"
    return "stay_manager_runtime_diagnostic"


def _case(case_id: str, blockers: list[str], observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": _status(blockers),
        "blockers": blockers,
        "observed": observed,
    }


def _gate_status(gate: dict[str, Any] | None) -> str:
    return str(_dict(gate).get("status") or "")


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT14h limited-live ladder closeout artifact.")
    parser.add_argument("--gate-ledger", type=Path, default=DEFAULT_GATE_LEDGER_PATH)
    parser.add_argument("--gate-artifact", type=Path, action="append", default=[])
    parser.add_argument("--live-decision-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    gate_ledger = yaml.safe_load(args.gate_ledger.read_text(encoding="utf-8"))
    gate_artifacts: dict[str, dict[str, Any]] = {}
    for artifact_path in args.gate_artifact:
        artifact = read_json_artifact(artifact_path)
        gate_id = str(artifact.get("target_manager_runtime_gate") or "")
        gate_artifacts[gate_id] = artifact
    artifact = build_rt14h_limited_live_ladder_closeout(
        gate_ledger=gate_ledger,
        gate_artifacts=gate_artifacts,
        live_decision_pack=read_json_artifact(args.live_decision_pack),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
